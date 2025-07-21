#!/usr/bin/env python3
"""
Health check script for HLS streaming service.
"""

import os
import sys
import glob
import time

def main():
    """
    Perform health check for HLS streaming processes.
    
    Checks if at least one HLS stream is being generated
    by looking for recent m3u8 files.
    """
    try:
        # Look for HLS playlist files
        playlist_pattern = "/tmp/data/hls/*/index.m3u8"
        playlists = glob.glob(playlist_pattern)
        
        if not playlists:
            print("No HLS playlists found - service starting up")
            sys.exit(1)
        
        # Check if at least one playlist was updated recently (within 60 seconds)
        current_time = time.time()
        recent_updates = 0
        
        for playlist in playlists:
            if os.path.exists(playlist):
                file_age = current_time - os.path.getmtime(playlist)
                if file_age < 60:
                    recent_updates += 1
        
        if recent_updates > 0:
            print(f"Health check passed - {recent_updates} active streams")
            sys.exit(0)
        else:
            print("Health check failed - no recent playlist updates")
            sys.exit(1)
            
    except Exception as e:
        print(f"Health check error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()