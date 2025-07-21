#!/usr/bin/env python3
"""
NGINX Log Monitor - Real-time monitoring of HLS streaming logs for listener analytics.

Features:
- Real-time monitoring of NGINX session logs
- Batch processing and GraphQL submission every 10 seconds
- Unique user tracking via anonymous_session_id
- Robust error handling and reconnection logic
- ListeningEvents data collection and submission
"""

import os
import sys
import time
import json
import logging
import requests
import threading
import re
from datetime import datetime, timezone
from typing import Dict, List, Set, Optional
from pathlib import Path
from collections import defaultdict, deque
import subprocess

class LogMonitor:
    def __init__(self):
        """Initialize the log monitor with configuration."""
        self.setup_logging()
        self.load_config()
        self.session_events: Dict[str, Dict] = {}
        self.batch_queue: List[Dict] = []
        self.active_sessions: Set[str] = set()
        self.running = True
        self.last_batch_time = time.time()
        self.log_position = 0
        
    def setup_logging(self):
        """Configure logging for the log monitor."""
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
        self.batch_interval = int(os.getenv('BATCH_INTERVAL_SECONDS', '10'))
        self.log_file_path = os.getenv('NGINX_LOG_PATH', '/var/log/nginx/session_access.log')
        self.session_timeout = int(os.getenv('SESSION_TIMEOUT_MINUTES', '5')) * 60
        
        self.logger.info(f"Log Monitor configured - GraphQL: {self.graphql_endpoint}")
        self.logger.info(f"Monitoring log file: {self.log_file_path}")
        
    def parse_log_line(self, line: str) -> Optional[Dict]:
        """
        Parse a single NGINX log line and extract relevant information.
        
        Expected format from nginx.conf:
        '$remote_addr - $remote_user [$time_local] "$request" $status $body_bytes_sent 
        "$http_referer" "$http_user_agent" anonymous_session_id="$anonymous_session_id" 
        station="$station_slug" request_time=$request_time upstream_response_time=$upstream_response_time'
        
        Args:
            line: Raw log line from NGINX
            
        Returns:
            Parsed log entry dictionary or None if parsing fails
        """
        try:
            # Regex pattern to match the custom log format
            pattern = (
                r'(?P<remote_addr>\S+) - (?P<remote_user>\S+) '
                r'\[(?P<time_local>[^\]]+)\] '
                r'"(?P<request>[^"]+)" '
                r'(?P<status>\d+) '
                r'(?P<body_bytes_sent>\d+) '
                r'"(?P<http_referer>[^"]*)" '
                r'"(?P<http_user_agent>[^"]*)" '
                r'anonymous_session_id="(?P<anonymous_session_id>[^"]+)" '
                r'station="(?P<station>[^"]*)" '
                r'request_time=(?P<request_time>[\d.-]+) '
                r'upstream_response_time=(?P<upstream_response_time>[\d.-]+|-)'
            )
            
            match = re.match(pattern, line.strip())
            if not match:
                return None
                
            data = match.groupdict()
            
            # Parse timestamp
            try:
                timestamp = datetime.strptime(data['time_local'], '%d/%b/%Y:%H:%M:%S %z')
            except ValueError:
                # Fallback to current time if parsing fails
                timestamp = datetime.now(timezone.utc)
            
            # Extract request method and URI
            request_parts = data['request'].split(' ')
            method = request_parts[0] if request_parts else 'GET'
            uri = request_parts[1] if len(request_parts) > 1 else '/'
            
            # Only process HLS requests (m3u8 and ts files)
            if not (uri.endswith('.m3u8') or uri.endswith('.ts') or '/hls/' in uri):
                return None
            
            # Extract station from URI if not in logs
            if data['station'] == 'unknown' or not data['station']:
                uri_match = re.search(r'/hls/([^/]+)/', uri)
                if uri_match:
                    data['station'] = uri_match.group(1)
                else:
                    return None  # Skip if we can't determine the station
            
            return {
                'timestamp': timestamp,
                'ip_address': data['remote_addr'],
                'session_id': data['anonymous_session_id'],
                'station_slug': data['station'],
                'user_agent': data['http_user_agent'],
                'referer': data['http_referer'],
                'status': int(data['status']),
                'bytes_sent': int(data['body_bytes_sent']),
                'request_time': float(data['request_time']) if data['request_time'] != '-' else 0.0,
                'method': method,
                'uri': uri,
                'is_playlist': uri.endswith('.m3u8'),
                'is_segment': uri.endswith('.ts'),
            }
            
        except Exception as e:
            self.logger.debug(f"Error parsing log line: {e} - Line: {line[:100]}...")
            return None
    
    def create_listening_event(self, session_id: str, station_slug: str, event_data: Dict) -> Dict:
        """
        Create a listening event for GraphQL submission.
        
        Args:
            session_id: Anonymous session ID
            station_slug: Station identifier
            event_data: Parsed log event data
            
        Returns:
            Listening event dictionary
        """
        return {
            'anonymous_session_id': session_id,
            'station_slug': station_slug,
            'ip_address': event_data['ip_address'],
            'user_agent': event_data['user_agent'],
            'timestamp': event_data['timestamp'].isoformat(),
            'event_type': 'playlist_request' if event_data['is_playlist'] else 'segment_request',
            'bytes_transferred': event_data['bytes_sent'],
            'request_duration': event_data['request_time'],
            'status_code': event_data['status']
        }
    
    def submit_batch_to_graphql(self, events: List[Dict]):
        """
        Submit a batch of listening events to the GraphQL endpoint.
        
        Args:
            events: List of listening event dictionaries
        """
        if not events:
            return
            
        mutation = """
        mutation SubmitListeningEvents($events: [ListeningEventInput!]!) {
            submitListeningEvents(events: $events) {
                success
                message
                processed_count
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
                    'variables': {'events': events}
                },
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'errors' not in data:
                    result = data.get('data', {}).get('submitListeningEvents', {})
                    processed = result.get('processed_count', len(events))
                    self.logger.info(f"Submitted {processed}/{len(events)} listening events successfully")
                else:
                    self.logger.error(f"GraphQL errors in batch submission: {data['errors']}")
            else:
                self.logger.error(f"Batch submission failed: {response.status_code} - {response.text[:200]}")
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Network error submitting batch: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error submitting batch: {e}")
    
    def process_events_batch(self):
        """Process accumulated events and submit to GraphQL."""
        if not self.batch_queue:
            return
        
        # Group events by session and station for deduplication
        session_events = defaultdict(list)
        unique_events = []
        
        for event in self.batch_queue:
            key = f"{event['anonymous_session_id']}:{event['station_slug']}"
            session_events[key].append(event)
        
        # Create consolidated events per session-station combination
        for key, events in session_events.items():
            # Use the latest event as the representative
            latest_event = max(events, key=lambda x: x['timestamp'])
            
            # Calculate total bytes and request count
            total_bytes = sum(event['bytes_transferred'] for event in events)
            request_count = len(events)
            
            # Update the representative event
            latest_event['bytes_transferred'] = total_bytes
            latest_event['request_count'] = request_count
            
            unique_events.append(latest_event)
        
        # Submit the batch
        self.logger.debug(f"Processing batch of {len(unique_events)} unique listening events from {len(self.batch_queue)} log entries")
        self.submit_batch_to_graphql(unique_events)
        
        # Clear the batch queue
        self.batch_queue.clear()
    
    def monitor_log_file(self):
        """Monitor the NGINX log file for new entries."""
        self.logger.info(f"Starting log file monitoring: {self.log_file_path}")
        
        while self.running:
            try:
                if not os.path.exists(self.log_file_path):
                    self.logger.warning(f"Log file not found: {self.log_file_path}. Waiting...")
                    time.sleep(5)
                    continue
                
                # Use tail -f to follow the log file
                process = subprocess.Popen(
                    ['tail', '-f', self.log_file_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                    bufsize=1
                )
                
                self.logger.info("Connected to log file, monitoring for new entries...")
                
                while self.running:
                    try:
                        line = process.stdout.readline()
                        if not line:
                            break
                            
                        # Parse the log line
                        parsed = self.parse_log_line(line)
                        if parsed:
                            # Create listening event
                            event = self.create_listening_event(
                                parsed['session_id'],
                                parsed['station_slug'],
                                parsed
                            )
                            self.batch_queue.append(event)
                            
                            # Track active sessions
                            self.active_sessions.add(parsed['session_id'])
                            
                    except Exception as e:
                        self.logger.error(f"Error processing log line: {e}")
                        continue
                        
            except subprocess.CalledProcessError as e:
                self.logger.error(f"Error running tail command: {e}")
                time.sleep(5)
            except Exception as e:
                self.logger.error(f"Error in log monitoring: {e}")
                time.sleep(5)
                
        self.logger.info("Log file monitoring stopped")
    
    def batch_processor(self):
        """Background thread to process batches every N seconds."""
        while self.running:
            try:
                time.sleep(self.batch_interval)
                if not self.running:
                    break
                    
                if self.batch_queue:
                    self.logger.debug(f"Processing batch with {len(self.batch_queue)} events")
                    self.process_events_batch()
                    
            except Exception as e:
                self.logger.error(f"Error in batch processor: {e}")
    
    def cleanup_old_sessions(self):
        """Clean up old session tracking data."""
        while self.running:
            try:
                time.sleep(60)  # Clean up every minute
                if not self.running:
                    break
                    
                current_time = time.time()
                old_sessions = []
                
                for session_id in list(self.active_sessions):
                    # Remove sessions that haven't been active for the timeout period
                    # This is a simple cleanup - in production you might want more sophisticated logic
                    pass  # Implementation would depend on session tracking needs
                    
            except Exception as e:
                self.logger.error(f"Error in session cleanup: {e}")
    
    def shutdown(self):
        """Gracefully shutdown the log monitor."""
        self.logger.info("Shutting down log monitor...")
        self.running = False
        
        # Process any remaining events
        if self.batch_queue:
            self.logger.info(f"Processing final batch of {len(self.batch_queue)} events")
            self.process_events_batch()
        
        self.logger.info("Log monitor shutdown complete")
    
    def run(self):
        """Main event loop for the log monitor."""
        self.logger.info("Starting NGINX Log Monitor...")
        
        # Start background threads
        batch_thread = threading.Thread(target=self.batch_processor, daemon=True)
        batch_thread.start()
        
        cleanup_thread = threading.Thread(target=self.cleanup_old_sessions, daemon=True)
        cleanup_thread.start()
        
        try:
            # Main log monitoring loop
            self.monitor_log_file()
        except KeyboardInterrupt:
            self.logger.info("Received shutdown signal")
        except Exception as e:
            self.logger.error(f"Fatal error in log monitor: {e}")
        finally:
            self.shutdown()

def main():
    """Main entry point for the log monitor."""
    try:
        monitor = LogMonitor()
        monitor.run()
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()