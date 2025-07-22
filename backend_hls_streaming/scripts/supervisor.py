#!/usr/bin/env python3
"""
Supervisor script to run both HLS Manager and Log Monitor simultaneously.

This script manages both processes:
- HLS Manager: Manages ffmpeg processes for HLS streaming
- Log Monitor: Monitors NGINX logs and sends analytics to backend
"""

import os
import sys
import time
import signal
import logging
import subprocess
import threading
from pathlib import Path
import json
from datetime import datetime

class ProcessSupervisor:
    def __init__(self):
        """Initialize the process supervisor."""
        self.setup_logging()
        self.processes = {}
        self.running = True
        self.log_processes = os.getenv('LOG_PROCESSES', 'true').lower() == 'true'
        self.log_ffmpeg = os.getenv('LOG_FFMPEG', 'true').lower() == 'true'
        self.log_nginx = os.getenv('LOG_NGINX', 'true').lower() == 'true'
        self.detailed_logging = os.getenv('DETAILED_LOGGING', 'false').lower() == 'true'
        
    def setup_logging(self):
        """Configure logging for the supervisor."""
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
        self.logger = logging.getLogger('supervisor')
        
        # Log configuration at startup
        self.logger.info(f"Logging configured - Level: {log_level}")
        self.logger.info(f"Environment variables: LOG_PROCESSES={os.getenv('LOG_PROCESSES', 'true')}, LOG_FFMPEG={os.getenv('LOG_FFMPEG', 'true')}, LOG_NGINX={os.getenv('LOG_NGINX', 'true')}")
        
    def start_process(self, name: str, command: list, cwd: str = None, env: dict = None):
        """Start a managed process."""
        try:
            cmd_str = ' '.join(command)
            self.logger.info(f"Starting {name}...")
            if self.detailed_logging:
                self.logger.debug(f"Command: {cmd_str}")
                self.logger.debug(f"Working directory: {cwd}")
                if env:
                    self.logger.debug(f"Environment: {json.dumps(env, indent=2)}")
            
            # Prepare environment
            process_env = os.environ.copy()
            if env:
                process_env.update(env)
            
            process = subprocess.Popen(
                command,
                cwd=cwd,
                env=process_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            self.processes[name] = {
                'process': process,
                'command': command,
                'cwd': cwd,
                'env': env,
                'start_time': time.time(),
                'restart_count': 0,
                'cmd_str': cmd_str
            }
            
            # Start log forwarding thread
            log_thread = threading.Thread(
                target=self.forward_logs, 
                args=(name, process), 
                daemon=True
            )
            log_thread.start()
            
            self.logger.info(f"{name} started successfully (PID: {process.pid}, Command: {cmd_str})")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start {name}: {e}")
            return False
    
    def forward_logs(self, name: str, process: subprocess.Popen):
        """Forward process logs with proper prefixes."""
        try:
            # Check if we should log this process
            should_log = self.log_processes
            if name == 'nginx' and not self.log_nginx:
                should_log = False
            elif name == 'hls_manager' and 'ffmpeg' in name and not self.log_ffmpeg:
                should_log = False
                
            while process.poll() is None and self.running:
                line = process.stdout.readline()
                if line and should_log:
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]
                    # Enhanced log formatting with timestamps
                    if self.detailed_logging:
                        print(f"[{timestamp}] [{name}] {line.rstrip()}")
                    else:
                        print(f"[{name}] {line.rstrip()}")
                        
                    # Flush immediately for real-time logs
                    sys.stdout.flush()
        except Exception as e:
            self.logger.error(f"Error forwarding logs for {name}: {e}")
    
    def check_processes(self):
        """Check process health and restart if needed."""
        for name, proc_info in list(self.processes.items()):
            process = proc_info['process']
            
            if process.poll() is not None:
                # Process has terminated
                exit_code = process.returncode
                runtime = time.time() - proc_info['start_time']
                
                if exit_code == 0:
                    self.logger.info(f"{name} exited cleanly after {runtime:.1f}s")
                else:
                    self.logger.error(f"{name} crashed with exit code {exit_code} after {runtime:.1f}s")
                    
                    # Restart if it didn't run for at least 30 seconds and restart count < 5
                    if runtime > 30 and proc_info['restart_count'] < 5:
                        self.logger.info(f"Attempting to restart {name} (attempt {proc_info['restart_count'] + 1}/5)")
                        proc_info['restart_count'] += 1
                        
                        # Restart the process
                        if self.start_process(name, proc_info['command'], proc_info['cwd'], proc_info.get('env')):
                            self.logger.info(f"{name} restarted successfully")
                        else:
                            self.logger.error(f"Failed to restart {name}")
                            del self.processes[name]
                    else:
                        self.logger.error(f"{name} will not be restarted (runtime: {runtime:.1f}s, restarts: {proc_info['restart_count']})")
                        del self.processes[name]
    
    def stop_process(self, name: str):
        """Stop a managed process."""
        if name in self.processes:
            process = self.processes[name]['process']
            self.logger.info(f"Stopping {name}...")
            
            try:
                # Graceful termination
                process.terminate()
                
                # Wait up to 10 seconds for graceful shutdown
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    # Force kill if graceful shutdown failed
                    self.logger.warning(f"Force killing {name}")
                    process.kill()
                    process.wait()
                
                self.logger.info(f"{name} stopped")
                del self.processes[name]
                
            except Exception as e:
                self.logger.error(f"Error stopping {name}: {e}")
    
    def shutdown(self):
        """Gracefully shutdown all processes."""
        self.logger.info("Shutting down all processes...")
        self.running = False
        
        for name in list(self.processes.keys()):
            self.stop_process(name)
        
        self.logger.info("Supervisor shutdown complete")
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, initiating shutdown...")
        self.shutdown()
        sys.exit(0)
    
    def run(self):
        """Main supervisor loop."""
        self.logger.info("Starting Process Supervisor for HLS Streaming Service")
        
        # Set up signal handlers
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
        
        # Get script directory
        script_dir = Path(__file__).parent
        
        # Start HLS Manager
        hls_manager_cmd = ['python3', str(script_dir / 'hls_manager.py')]
        if not self.start_process('hls_manager', hls_manager_cmd):
            self.logger.error("Failed to start HLS Manager")
            return False
        
        # Wait a bit for HLS manager to initialize
        time.sleep(5)
        
        # Start NGINX
        nginx_cmd = ['nginx', '-g', 'daemon off;', '-c', '/app/nginx/nginx.conf']
        if not self.start_process('nginx', nginx_cmd):
            self.logger.error("Failed to start NGINX")
            return False
        
        # Wait for NGINX to start
        time.sleep(3)
        
        # Start Log Monitor
        log_monitor_cmd = ['python3', str(script_dir / 'log_monitor.py')]
        if not self.start_process('log_monitor', log_monitor_cmd):
            self.logger.error("Failed to start Log Monitor")
            return False
        
        self.logger.info("All processes started successfully")
        
        # Start nginx log monitoring if enabled
        if self.log_nginx:
            self.start_nginx_log_monitoring()
        
        # Start process status reporting
        status_thread = threading.Thread(target=self.status_reporter, daemon=True)
        status_thread.start()
        
        try:
            # Main monitoring loop
            while self.running:
                self.check_processes()
                
                # Exit if no processes are running
                if not self.processes:
                    self.logger.error("No processes running, exiting")
                    break
                
                time.sleep(10)  # Check every 10 seconds
                
        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt")
        except Exception as e:
            self.logger.error(f"Error in supervisor loop: {e}")
        finally:
            self.shutdown()
        
        return True
    
    def start_nginx_log_monitoring(self):
        """Start monitoring nginx logs if enabled."""
        try:
            nginx_access_log = '/tmp/nginx_access.log'
            nginx_error_log = '/tmp/nginx_error.log'
            
            if os.path.exists(nginx_access_log):
                access_thread = threading.Thread(
                    target=self.monitor_nginx_log, 
                    args=('nginx_access', nginx_access_log), 
                    daemon=True
                )
                access_thread.start()
                self.logger.info("Started nginx access log monitoring")
            
            if os.path.exists(nginx_error_log):
                error_thread = threading.Thread(
                    target=self.monitor_nginx_log, 
                    args=('nginx_error', nginx_error_log), 
                    daemon=True
                )
                error_thread.start()
                self.logger.info("Started nginx error log monitoring")
                
        except Exception as e:
            self.logger.error(f"Failed to start nginx log monitoring: {e}")
    
    def monitor_nginx_log(self, log_name: str, log_path: str):
        """Monitor nginx log files and forward output."""
        try:
            # Use tail -f to follow the log file
            process = subprocess.Popen(
                ['tail', '-f', log_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            while self.running and process.poll() is None:
                line = process.stdout.readline()
                if line:
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S,%f')[:-3] if self.detailed_logging else ''
                    prefix = f"[{timestamp}] " if timestamp else ""
                    print(f"{prefix}[{log_name}] {line.rstrip()}")
                    sys.stdout.flush()
                    
        except Exception as e:
            self.logger.error(f"Error monitoring {log_name}: {e}")
    
    def status_reporter(self):
        """Periodically report process status."""
        try:
            while self.running:
                time.sleep(30)  # Report every 30 seconds
                if self.detailed_logging:
                    self.report_process_status()
        except Exception as e:
            self.logger.error(f"Error in status reporter: {e}")
    
    def report_process_status(self):
        """Report current status of all processes."""
        try:
            status_info = []
            for name, proc_info in self.processes.items():
                process = proc_info['process']
                runtime = time.time() - proc_info['start_time']
                
                if process.poll() is None:
                    status = "RUNNING"
                    status_info.append(f"{name}: {status} (PID: {process.pid}, Runtime: {runtime:.1f}s)")
                else:
                    status = f"DEAD (exit: {process.returncode})"
                    status_info.append(f"{name}: {status}")
            
            if status_info:
                self.logger.info(f"Process Status - {', '.join(status_info)}")
            
        except Exception as e:
            self.logger.error(f"Error reporting process status: {e}")

def main():
    """Main entry point."""
    try:
        supervisor = ProcessSupervisor()
        success = supervisor.run()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Fatal supervisor error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()