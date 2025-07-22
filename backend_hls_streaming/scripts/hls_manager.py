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
import signal

class HLSManager:
    def __init__(self):
        """Initialize HLS Manager with configuration and logging."""
        # Set logging configuration first
        self.detailed_logging = os.getenv('DETAILED_LOGGING', 'false').lower() == 'true'
        self.log_ffmpeg = os.getenv('LOG_FFMPEG', 'true').lower() == 'true'
        
        self.setup_logging()
        
        # Initialize cache settings before load_config() since it references them in logging
        self.cache_file = Path('/tmp/data/stations_cache.json')
        self.cache_ttl_hours = int(os.getenv('CACHE_TTL_HOURS', '24'))
        
        self.load_config()
        self.active_processes: Dict[str, dict] = {}  # Store process info and metadata
        self.station_metadata: Dict[str, dict] = {}
        self.last_station_fetch = datetime.min
        self.running = True
        self.cached_stations: List[dict] = []
        
    def setup_logging(self):
        """Configure logging for the HLS manager."""
        log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
        log_format = os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # Enable more verbose logging if requested
        if os.getenv('VERBOSE_LOGGING', 'false').lower() == 'true':
            log_format = '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
        
        logging.basicConfig(
            level=getattr(logging, log_level),
            format=log_format,
            force=True
        )
        self.logger = logging.getLogger(__name__)
        
        # Log configuration
        self.logger.info(f"HLS Manager logging configured - Level: {log_level}")
        self.logger.info(f"Environment: LOG_FFMPEG={os.getenv('LOG_FFMPEG', 'true')}, DETAILED_LOGGING={os.getenv('DETAILED_LOGGING', 'false')}")
        
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
        if self.detailed_logging:
            self.logger.debug(f"Configuration: refresh_interval={self.refresh_interval}s, max_log_size={self.max_log_size}B")
            self.logger.debug(f"Directories: data={self.base_data_dir}, logs={self.base_log_dir}")
            self.logger.debug(f"Cache: file={self.cache_file}, ttl={self.cache_ttl_hours}h")
        
        # Load cached stations on startup
        self.load_cached_stations()
        
    def save_cached_stations(self, stations: List[dict]):
        """Save successful station data to cache file."""
        try:
            cache_data = {
                'timestamp': datetime.now().isoformat(),
                'stations': stations
            }
            
            # Ensure parent directory exists
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
            
            self.cached_stations = stations
            self.logger.info(f"Cached {len(stations)} stations to {self.cache_file}")
            
        except Exception as e:
            self.logger.error(f"Error saving stations cache: {e}")
    
    def load_cached_stations(self):
        """Load stations from cache file if available and valid."""
        try:
            if not self.cache_file.exists():
                self.logger.info("No stations cache file found")
                return
            
            with open(self.cache_file, 'r') as f:
                cache_data = json.load(f)
            
            # Check cache age
            cache_timestamp = datetime.fromisoformat(cache_data['timestamp'])
            cache_age = datetime.now() - cache_timestamp
            
            if cache_age.total_seconds() / 3600 > self.cache_ttl_hours:
                self.logger.warning(f"Stations cache is stale ({cache_age.total_seconds() / 3600:.1f}h old), ignoring")
                return
            
            self.cached_stations = cache_data.get('stations', [])
            self.logger.info(f"Loaded {len(self.cached_stations)} stations from cache (age: {cache_age.total_seconds() / 60:.1f}m)")
            
        except Exception as e:
            self.logger.error(f"Error loading stations cache: {e}")
            self.cached_stations = []
    
    def get_stations_from_graphql(self) -> List[dict]:
        """
        Fetch stations that require HLS streaming from GraphQL endpoint.
        
        Returns:
            List of station dictionaries with id, title, slug, stream_url
        """
        query = """
        query GetHLSStations {
            stations {
                id
                title
                slug
                stream_url
                generate_hls_stream
                disabled
                now_playing {
                    id
                    song {
                        id
                        name
                        artist {
                            id
                            name
                        }
                    }
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
                
                # Get all stations from response
                all_stations = data.get('data', {}).get('stations', [])
                
                # Filter for stations that need HLS streaming and are not disabled
                hls_stations = [
                    station for station in all_stations
                    if station.get('generate_hls_stream', False) and not station.get('disabled', False)
                ]
                
                if self.detailed_logging:
                    self.logger.debug(f"📊 Retrieved {len(all_stations)} total stations, {len(hls_stations)} require HLS streaming")
                    for station in hls_stations:
                        metadata_info = ""
                        if station.get('now_playing') and station['now_playing'].get('song'):
                            song = station['now_playing']['song']
                            artist_name = song.get('artist', {}).get('name', 'Unknown') if song.get('artist') else 'Unknown'
                            song_name = song.get('name', 'Unknown')
                            metadata_info = f" (Now: {artist_name} - {song_name})"
                        self.logger.debug(f"  🎵 {station['title']} ({station['slug']}): {station['stream_url']}{metadata_info}")
                
                # Save successful response to cache
                self.save_cached_stations(hls_stations)
                
                return hls_stations
            else:
                self.logger.error(f"GraphQL request failed: {response.status_code} - {response.text}")
                # Fall back to cached data
                if self.cached_stations:
                    self.logger.warning(f"📋 Backend down, using {len(self.cached_stations)} cached stations as fallback")
                    return self.cached_stations
                else:
                    self.logger.error("❌ No cached stations available for fallback")
                    return []
                
        except Exception as e:
            self.logger.error(f"Error fetching stations from GraphQL: {e}")
            # Fall back to cached data
            if self.cached_stations:
                self.logger.warning(f"📋 Backend unreachable, using {len(self.cached_stations)} cached stations as fallback")
                return self.cached_stations
            else:
                self.logger.error("❌ No cached stations available for fallback")
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
    
    def cleanup_station_hls_data(self, station_slug: str):
        """
        Clean up HLS data directory for a station.
        
        Args:
            station_slug: The station slug to clean up
        """
        station_data_dir = self.base_data_dir / station_slug
        
        if station_data_dir.exists():
            try:
                # Remove all files in the station directory
                for file_path in station_data_dir.glob('*'):
                    if file_path.is_file():
                        file_path.unlink()
                        if self.detailed_logging:
                            self.logger.debug(f"Removed HLS file: {file_path}")
                
                self.logger.info(f"Cleaned up HLS data for station: {station_slug}")
                
            except Exception as e:
                self.logger.error(f"Error cleaning up HLS data for {station_slug}: {e}")

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
        
        # Create station data directory and clean up any existing HLS files
        station_data_dir = self.base_data_dir / station_slug
        station_data_dir.mkdir(exist_ok=True)
        
        # Clean up any existing HLS files before starting
        self.cleanup_station_hls_data(station_slug)
        
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
                y=None,  # Equivalent to -y flag
                abort_on='empty_output_stream',
                **{
                    'c:a': 'libfdk_aac',
                    'profile:a': 'aac_he',
                    'b:a': '64k',
                    'flags': '+global_header',
                    'async': 1,
                    'ac': 2,
                    'ar': 44100,
                    'map': '0:a:0',
                    'bufsize': '30000000',
                    'f': 'hls',
                    'hls_init_time': 6,  # Increased from 2s to 6s for initial buffering
                    'hls_time': 4,       # Reduced from 5s to 4s for more granular segments
                    'hls_list_size': 60, # Reduced from 300 to 60 (4 minutes of segments at 4s each)
                    'hls_delete_threshold': 12,  # Keep at least 12 segments (48s) before deletion
                    'hls_flags': 'delete_segments+independent_segments+split_by_time',
                    'hls_start_number_source': 'epoch',
                    'hls_segment_filename': str(station_data_dir / '%d.ts'),
                    'master_pl_publish_rate': 1,
                    'sc_threshold': 0,
                    # Additional resilience options
                    'hls_segment_options': 'mpegts_flags=+initial_discontinuity',
                    'max_delay': 5000000,  # 5 seconds max delay tolerance
                    'fflags': '+genpts+discardcorrupt',
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
                    self.logger.warning(f"Force killing FFmpeg process for {station_slug} (PID: {process.pid})")
                    process.kill()
                    process.wait()
                
                runtime = datetime.now() - process_info['start_time'] if isinstance(self.active_processes[station_slug], dict) else 'unknown'
                self.logger.info(f"✓ Stopped FFmpeg process for {station_slug} (Runtime: {runtime})")
                
                # Log final status to station log if enabled
                if (self.log_ffmpeg and isinstance(self.active_processes[station_slug], dict) 
                    and 'log_file' in self.active_processes[station_slug]):
                    try:
                        with open(self.active_processes[station_slug]['log_file'], 'a') as log_f:
                            log_f.write(f"\n=== FFmpeg process stopped at {datetime.now()} (Runtime: {runtime}) ===\n")
                            log_f.flush()
                    except Exception:
                        pass  # Don't let logging errors break the stop process
                
            except Exception as e:
                self.logger.error(f"✗ Error stopping FFmpeg process for {station_slug}: {e}")
                if self.detailed_logging:
                    import traceback
                    self.logger.debug(f"Traceback: {traceback.format_exc()}")
            
            finally:
                # Clean up HLS data files
                self.cleanup_station_hls_data(station_slug)
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
            if self.detailed_logging:
                self.logger.debug(f"No active process found for {station_slug}")
            return False
            
        process_info = self.active_processes[station_slug]
        process = process_info['process'] if isinstance(process_info, dict) else process_info
        
        # Check if process is still running
        if process.poll() is not None:
            exit_code = process.returncode
            runtime = datetime.now() - process_info['start_time'] if isinstance(process_info, dict) else 'unknown'
            self.logger.warning(f"⚠️  FFmpeg process for {station_slug} has terminated (exit code: {exit_code}, runtime: {runtime})")
            return False
        
        # Get process info for detailed logging
        if isinstance(process_info, dict):
            start_time = process_info['start_time']
            runtime = datetime.now() - start_time
        else:
            runtime = 'unknown'
        
        # Check if HLS playlist exists and is recent
        playlist_file = self.base_data_dir / station_slug / 'index.m3u8'
        if playlist_file.exists():
            # Check if file was modified in the last 60 seconds
            file_age = time.time() - playlist_file.stat().st_mtime
            if file_age > 60:
                self.logger.warning(f"⚠️  HLS playlist for {station_slug} is stale ({file_age:.1f}s old, runtime: {runtime})")
                return False
            elif self.detailed_logging:
                self.logger.debug(f"✓ {station_slug}: playlist fresh ({file_age:.1f}s old, runtime: {runtime})")
        else:
            # Allow 30 seconds for initial playlist creation
            if isinstance(process_info, dict):
                process_age = (datetime.now() - process_info['start_time']).total_seconds()
            else:
                try:
                    p = psutil.Process(process.pid)
                    process_age = time.time() - p.create_time()
                except (psutil.NoSuchProcess, AttributeError):
                    process_age = 30  # Assume it's been running long enough
                    
            if process_age > 30:
                self.logger.warning(f"⚠️  No HLS playlist found for {station_slug} after {process_age:.1f}s")
                return False
            elif self.detailed_logging:
                self.logger.debug(f"⏳ {station_slug}: waiting for playlist (process age: {process_age:.1f}s)")
        
        if self.detailed_logging:
            try:
                # Get memory and CPU usage
                p = psutil.Process(process.pid)
                memory_mb = p.memory_info().rss / 1024 / 1024
                cpu_percent = p.cpu_percent()
                self.logger.debug(f"✓ {station_slug}: healthy (PID: {process.pid}, RAM: {memory_mb:.1f}MB, CPU: {cpu_percent:.1f}%, Runtime: {runtime})")
            except (psutil.NoSuchProcess, AttributeError):
                pass  # Process might have just terminated
        
        return True
    
    def report_process_status(self):
        """Report detailed status of all FFmpeg processes."""
        if not self.active_processes:
            self.logger.info("📊 No active FFmpeg processes")
            return
        
        status_lines = []
        total_memory = 0
        
        for station_slug, process_info in self.active_processes.items():
            try:
                process = process_info['process'] if isinstance(process_info, dict) else process_info
                
                if process.poll() is None:
                    # Process is running
                    p = psutil.Process(process.pid)
                    memory_mb = p.memory_info().rss / 1024 / 1024
                    total_memory += memory_mb
                    cpu_percent = p.cpu_percent()
                    
                    if isinstance(process_info, dict):
                        runtime = datetime.now() - process_info['start_time']
                        station_title = process_info['station']['title'][:20] + '...' if len(process_info['station']['title']) > 20 else process_info['station']['title']
                    else:
                        runtime = 'unknown'
                        station_title = station_slug
                    
                    playlist_file = self.base_data_dir / station_slug / 'index.m3u8'
                    playlist_status = "📺" if playlist_file.exists() else "⏳"
                    
                    status_lines.append(
                        f"  {playlist_status} {station_slug} ({station_title}): "
                        f"PID {process.pid}, RAM {memory_mb:.1f}MB, CPU {cpu_percent:.1f}%, Runtime {runtime}"
                    )
                else:
                    status_lines.append(f"  ❌ {station_slug}: DEAD (exit: {process.returncode})")
                    
            except (psutil.NoSuchProcess, AttributeError) as e:
                status_lines.append(f"  ⚠️  {station_slug}: Process info unavailable ({e})")
        
        self.logger.info(f"📊 FFmpeg Process Status ({len(self.active_processes)} processes, {total_memory:.1f}MB total):")
        for line in status_lines:
            self.logger.info(line)
    
    def update_stations(self):
        """Update the list of active stations and manage ffmpeg processes."""
        self.logger.info("🔄 Fetching updated station list from GraphQL...")
        current_stations = self.get_stations_from_graphql()
        
        if not current_stations:
            self.logger.warning("⚠️  No stations retrieved from GraphQL")
            return
        
        self.logger.info(f"📋 Found {len(current_stations)} stations requiring HLS streaming")
        if self.detailed_logging:
            for station in current_stations:
                self.logger.debug(f"  - {station['title']} ({station['slug']}): {station['stream_url']}")
        
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
        
        # Stop all active processes (this will also clean up their HLS data)
        for station_slug in list(self.active_processes.keys()):
            self.stop_ffmpeg_process(station_slug)
        
        # Clean up any remaining HLS data directories
        try:
            if self.base_data_dir.exists():
                for station_dir in self.base_data_dir.glob('*'):
                    if station_dir.is_dir():
                        station_slug = station_dir.name
                        self.cleanup_station_hls_data(station_slug)
        except Exception as e:
            self.logger.error(f"Error during final HLS cleanup: {e}")
        
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