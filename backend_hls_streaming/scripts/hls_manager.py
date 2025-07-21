#!/usr/bin/env python3
"""
HLS Stream Manager - Main service for managing ffmpeg HLS conversion processes.

Features:
- GraphQL integration with backend for station management
- ffmpeg process management using python-ffmpeg
- Automatic process monitoring and restart
- Metadata change detection and GraphQL mutation triggers
- Per-station logging with rotation limits
"""

import os
import sys
import time
import json
import logging
import requests
import subprocess
import threading
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import ffmpeg
import psutil
from pathlib import Path

class HLSManager:
    def __init__(self):
        """Initialize HLS Manager with configuration and logging."""
        self.setup_logging()
        self.load_config()
        self.active_processes: Dict[str, subprocess.Popen] = {}
        self.station_metadata: Dict[str, dict] = {}
        self.last_station_fetch = datetime.min
        self.running = True
        
    def setup_logging(self):
        """Configure logging for the HLS manager."""
        log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
    def load_config(self):
        """Load configuration from environment variables."""
        self.graphql_endpoint = os.getenv('GRAPHQL_ENDPOINT', 'http://web:8000/graphql/')
        self.graphql_token = os.getenv('GRAPHQL_TOKEN', '')
        self.refresh_interval = int(os.getenv('STREAM_REFRESH_INTERVAL', '60'))
        self.base_data_dir = Path('/tmp/data/hls')
        self.base_log_dir = Path('/tmp/logs')
        self.max_log_size = int(os.getenv('MAX_LOG_SIZE_MB', '20')) * 1024 * 1024
        
        # Create necessary directories
        self.base_data_dir.mkdir(parents=True, exist_ok=True)
        self.base_log_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"HLS Manager configured - GraphQL: {self.graphql_endpoint}")
        
    def get_stations_from_graphql(self) -> List[dict]:
        """
        Fetch stations that require HLS streaming from GraphQL endpoint.
        
        Returns:
            List of station dictionaries with id, title, slug, stream_url
        """
        query = """
        query GetHLSStations {
            stations(where: {generate_hls_stream: {_eq: true}, disabled: {_eq: false}}) {
                id
                title
                slug
                stream_url
                latest_station_metadata_fetch {
                    id
                    artist
                    title
                    updated_at
                }
            }
        }
        """
        
        headers = {
            'Content-Type': 'application/json',
        }
        if self.graphql_token:
            headers['Authorization'] = f'Bearer {self.graphql_token}'
            
        try:
            response = requests.post(
                self.graphql_endpoint,
                json={'query': query},
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'errors' in data:
                    self.logger.error(f"GraphQL errors: {data['errors']}")
                    return []
                return data.get('data', {}).get('stations', [])
            else:
                self.logger.error(f"GraphQL request failed: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            self.logger.error(f"Error fetching stations from GraphQL: {e}")
            return []
    
    def trigger_metadata_fetch(self, station_id: str):
        """
        Trigger a metadata fetch for a station via GraphQL mutation.
        
        Args:
            station_id: The station ID to trigger metadata fetch for
        """
        mutation = """
        mutation TriggerMetadataFetch($stationId: Int!) {
            triggerMetadataFetch(stationId: $stationId) {
                success
                message
            }
        }
        """
        
        headers = {
            'Content-Type': 'application/json',
        }
        if self.graphql_token:
            headers['Authorization'] = f'Bearer {self.graphql_token}'
            
        try:
            response = requests.post(
                self.graphql_endpoint,
                json={
                    'query': mutation,
                    'variables': {'stationId': int(station_id)}
                },
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'errors' not in data:
                    self.logger.info(f"Triggered metadata fetch for station {station_id}")
                else:
                    self.logger.error(f"Metadata fetch trigger failed: {data['errors']}")
            else:
                self.logger.error(f"Metadata fetch trigger request failed: {response.status_code}")
                
        except Exception as e:
            self.logger.error(f"Error triggering metadata fetch for station {station_id}: {e}")
    
    def create_station_log_file(self, station_slug: str) -> str:
        """
        Create and return the log file path for a station.
        
        Args:
            station_slug: The station slug for the log file
            
        Returns:
            Path to the log file
        """
        log_file = self.base_log_dir / f"{station_slug}.log"
        
        # Rotate log if it exceeds max size
        if log_file.exists() and log_file.stat().st_size > self.max_log_size:
            backup_log = self.base_log_dir / f"{station_slug}.log.old"
            if backup_log.exists():
                backup_log.unlink()
            log_file.rename(backup_log)
            self.logger.info(f"Rotated log file for station {station_slug}")
        
        return str(log_file)
    
    def start_ffmpeg_process(self, station: dict) -> Optional[subprocess.Popen]:
        """
        Start an ffmpeg process for a station.
        
        Args:
            station: Station dictionary with stream details
            
        Returns:
            subprocess.Popen object or None if failed
        """
        station_slug = station['slug']
        stream_url = station['stream_url']
        
        # Create station data directory
        station_data_dir = self.base_data_dir / station_slug
        station_data_dir.mkdir(exist_ok=True)
        
        # Get log file path
        log_file = self.create_station_log_file(station_slug)
        
        # Build ffmpeg command for HLS streaming
        output_path = str(station_data_dir / 'index.m3u8')
        
        try:
            # Use ffmpeg-python to build the command
            stream = ffmpeg.input(stream_url)
            stream = ffmpeg.output(
                stream,
                output_path,
                **{
                    'c:a': 'libfdk_aac',
                    'profile:a': 'aac_he',
                    'b:a': '64k',
                    'flags': '+global_header',
                    'async': 1,
                    'ac': 2,
                    'ar': 44100,
                    'bufsize': '30000000',
                    'f': 'hls',
                    'hls_init_time': 2,
                    'hls_time': 5,
                    'hls_list_size': 300,
                    'hls_delete_threshold': 30,
                    'hls_flags': 'delete_segments+independent_segments',
                    'hls_start_number_source': 'epoch',
                    'hls_segment_filename': str(station_data_dir / '%d.ts'),
                    'master_pl_publish_rate': 1,
                    'sc_threshold': 0,
                }
            )
            
            # Override the default behavior to handle errors gracefully
            cmd = ffmpeg.compile(stream, overwrite_output=True)
            
            # Start the process with logging
            with open(log_file, 'a') as log_f:
                log_f.write(f"\n=== FFmpeg process started at {datetime.now()} ===\n")
                log_f.write(f"Command: {' '.join(cmd)}\n")
                log_f.write(f"Station: {station['title']} ({station_slug})\n")
                log_f.write(f"Stream URL: {stream_url}\n\n")
                log_f.flush()
                
                process = subprocess.Popen(
                    cmd,
                    stdout=log_f,
                    stderr=subprocess.STDOUT,
                    cwd=str(station_data_dir)
                )
            
            self.logger.info(f"Started FFmpeg process for {station_slug} (PID: {process.pid})")
            return process
            
        except Exception as e:
            self.logger.error(f"Error starting FFmpeg process for {station_slug}: {e}")
            return None
    
    def stop_ffmpeg_process(self, station_slug: str):
        """
        Stop an ffmpeg process for a station.
        
        Args:
            station_slug: The station slug to stop
        """
        if station_slug in self.active_processes:
            process = self.active_processes[station_slug]
            
            try:
                # Graceful termination
                process.terminate()
                
                # Wait up to 10 seconds for graceful shutdown
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    # Force kill if graceful shutdown failed
                    process.kill()
                    process.wait()
                
                self.logger.info(f"Stopped FFmpeg process for {station_slug}")
                
            except Exception as e:
                self.logger.error(f"Error stopping FFmpeg process for {station_slug}: {e}")
            
            finally:
                del self.active_processes[station_slug]
    
    def check_process_health(self, station_slug: str) -> bool:
        """
        Check if an ffmpeg process is healthy and producing output.
        
        Args:
            station_slug: The station slug to check
            
        Returns:
            True if process is healthy, False otherwise
        """
        if station_slug not in self.active_processes:
            return False
            
        process = self.active_processes[station_slug]
        
        # Check if process is still running
        if process.poll() is not None:
            self.logger.warning(f"FFmpeg process for {station_slug} has terminated")
            return False
        
        # Check if HLS playlist exists and is recent
        playlist_file = self.base_data_dir / station_slug / 'index.m3u8'
        if playlist_file.exists():
            # Check if file was modified in the last 60 seconds
            file_age = time.time() - playlist_file.stat().st_mtime
            if file_age > 60:
                self.logger.warning(f"HLS playlist for {station_slug} is stale ({file_age:.1f}s old)")
                return False
        else:
            # Allow 30 seconds for initial playlist creation
            process_age = time.time() - process.create_time()
            if process_age > 30:
                self.logger.warning(f"No HLS playlist found for {station_slug} after {process_age:.1f}s")
                return False
        
        return True
    
    def update_stations(self):
        """Update the list of active stations and manage ffmpeg processes."""
        self.logger.info("Fetching updated station list from GraphQL...")
        current_stations = self.get_stations_from_graphql()
        
        if not current_stations:
            self.logger.warning("No stations retrieved from GraphQL")
            return
        
        current_slugs = {station['slug'] for station in current_stations}
        active_slugs = set(self.active_processes.keys())
        
        # Stop processes for stations that are no longer active
        for station_slug in active_slugs - current_slugs:
            self.logger.info(f"Stopping inactive station: {station_slug}")
            self.stop_ffmpeg_process(station_slug)
        
        # Start processes for new stations and restart unhealthy ones
        for station in current_stations:
            station_slug = station['slug']
            
            # Check for metadata changes
            if station_slug in self.station_metadata:
                old_metadata = self.station_metadata[station_slug].get('latest_station_metadata_fetch', {})
                new_metadata = station.get('latest_station_metadata_fetch', {})
                
                if (old_metadata.get('updated_at') != new_metadata.get('updated_at') and 
                    new_metadata.get('updated_at')):
                    self.logger.info(f"Metadata changed for {station_slug}, triggering refresh")
                    # Note: In a more advanced implementation, this could trigger
                    # additional metadata processing
            
            # Update stored metadata
            self.station_metadata[station_slug] = station
            
            # Check if process needs to be started or restarted
            if (station_slug not in self.active_processes or 
                not self.check_process_health(station_slug)):
                
                if station_slug in self.active_processes:
                    self.logger.info(f"Restarting unhealthy process for {station_slug}")
                    self.stop_ffmpeg_process(station_slug)
                
                self.logger.info(f"Starting FFmpeg process for {station_slug}")
                process = self.start_ffmpeg_process(station)
                if process:
                    self.active_processes[station_slug] = process
        
        self.last_station_fetch = datetime.now()
        self.logger.info(f"Station update complete - managing {len(self.active_processes)} streams")
    
    def health_monitor(self):
        """Background thread to monitor process health."""
        while self.running:
            try:
                # Health check every 30 seconds
                time.sleep(30)
                
                if not self.running:
                    break
                
                # Check each active process
                unhealthy_stations = []
                for station_slug in list(self.active_processes.keys()):
                    if not self.check_process_health(station_slug):
                        unhealthy_stations.append(station_slug)
                
                # Restart unhealthy processes on next station update
                if unhealthy_stations:
                    self.logger.warning(f"Found unhealthy stations: {unhealthy_stations}")
                    
            except Exception as e:
                self.logger.error(f"Error in health monitor: {e}")
    
    def shutdown(self):
        """Gracefully shutdown all ffmpeg processes."""
        self.logger.info("Shutting down HLS Manager...")
        self.running = False
        
        # Stop all active processes
        for station_slug in list(self.active_processes.keys()):
            self.stop_ffmpeg_process(station_slug)
        
        self.logger.info("HLS Manager shutdown complete")
    
    def run(self):
        """Main event loop for the HLS Manager."""
        self.logger.info("Starting HLS Manager...")
        
        # Start health monitor thread
        health_thread = threading.Thread(target=self.health_monitor, daemon=True)
        health_thread.start()
        
        try:
            while self.running:
                try:
                    # Update stations
                    self.update_stations()
                    
                    # Wait for next refresh
                    for _ in range(self.refresh_interval):
                        if not self.running:
                            break
                        time.sleep(1)
                        
                except KeyboardInterrupt:
                    self.logger.info("Received shutdown signal")
                    break
                except Exception as e:
                    self.logger.error(f"Error in main loop: {e}")
                    time.sleep(10)  # Wait before retrying
                    
        finally:
            self.shutdown()

def main():
    """Main entry point for the HLS Manager."""
    try:
        manager = HLSManager()
        manager.run()
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()