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

class ProcessSupervisor:
    def __init__(self):
        """Initialize the process supervisor."""
        self.setup_logging()
        self.processes = {}
        self.running = True
        
    def setup_logging(self):
        """Configure logging for the supervisor."""
        log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('supervisor')
        
    def start_process(self, name: str, command: list, cwd: str = None):
        """Start a managed process."""
        try:
            self.logger.info(f"Starting {name}...")
            process = subprocess.Popen(
                command,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            self.processes[name] = {
                'process': process,
                'command': command,
                'cwd': cwd,
                'start_time': time.time(),
                'restart_count': 0
            }
            
            # Start log forwarding thread
            log_thread = threading.Thread(
                target=self.forward_logs, 
                args=(name, process), 
                daemon=True
            )
            log_thread.start()
            
            self.logger.info(f"{name} started successfully (PID: {process.pid})")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start {name}: {e}")
            return False
    
    def forward_logs(self, name: str, process: subprocess.Popen):
        """Forward process logs with proper prefixes."""
        try:
            while process.poll() is None and self.running:
                line = process.stdout.readline()
                if line:
                    # Forward with process name prefix
                    print(f"[{name}] {line.rstrip()}")
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
                        if self.start_process(name, proc_info['command'], proc_info['cwd']):
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