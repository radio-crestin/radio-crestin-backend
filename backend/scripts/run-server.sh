#!/bin/bash
set -e

# Global variables
RESTART_COUNT=0
MAX_RESTARTS=10
RESTART_DELAY=5
GUNICORN_PID=""

# Function to log messages with timestamp
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S'): $1"
}

# Function to cleanup processes on exit
cleanup() {
    log_message "Cleaning up processes..."
    if [ -n "$GUNICORN_PID" ] && kill -0 "$GUNICORN_PID" 2>/dev/null; then
        log_message "Terminating Gunicorn process (PID: $GUNICORN_PID)"
        kill -TERM "$GUNICORN_PID" 2>/dev/null || true
        sleep 2
        kill -KILL "$GUNICORN_PID" 2>/dev/null || true
    fi
    exit 0
}

# Function to check if Django application is responding
check_app_health() {
    local max_attempts=30
    local attempt=1
    
    log_message "Checking Django application health..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f -s -o /dev/null http://localhost:8080/health/ 2>/dev/null; then
            log_message "Django application is responding"
            return 0
        fi
        
        if [ $attempt -eq 1 ]; then
            log_message "Waiting for Django application to start..."
        fi
        
        sleep 2
        attempt=$((attempt + 1))
    done
    
    log_message "Django application failed to respond after $max_attempts attempts"
    return 1
}

# Function to start Gunicorn with auto-restart capability
start_gunicorn() {
    local config_file="$1"
    local mode="$2"
    
    while [ $RESTART_COUNT -lt $MAX_RESTARTS ]; do
        log_message "Starting Django $mode server (attempt $((RESTART_COUNT + 1))/$MAX_RESTARTS)..."
        
        # Start Gunicorn in background
        gunicorn --config "$config_file" superapp.wsgi:application &
        GUNICORN_PID=$!
        
        log_message "Gunicorn process started with PID: $GUNICORN_PID"
        
        # Wait a moment for Gunicorn to start
        sleep 3
        
        # Check if the process is still running
        if ! kill -0 "$GUNICORN_PID" 2>/dev/null; then
            log_message "Gunicorn process died immediately, restarting..."
            RESTART_COUNT=$((RESTART_COUNT + 1))
            sleep $RESTART_DELAY
            continue
        fi
        
        # Check if Django application is responding
        if check_app_health; then
            log_message "Django application started successfully"
            RESTART_COUNT=0  # Reset restart count on successful start
            
            # Monitor the process
            while kill -0 "$GUNICORN_PID" 2>/dev/null; do
                sleep 10
                
                # Periodic health check
                if ! curl -f -s -o /dev/null http://localhost:8080/health/ 2>/dev/null; then
                    log_message "Django application stopped responding, restarting..."
                    kill -TERM "$GUNICORN_PID" 2>/dev/null || true
                    sleep 2
                    kill -KILL "$GUNICORN_PID" 2>/dev/null || true
                    break
                fi
            done
            
            log_message "Gunicorn process (PID: $GUNICORN_PID) has stopped"
        else
            log_message "Django application failed to start properly"
            kill -TERM "$GUNICORN_PID" 2>/dev/null || true
            sleep 2
            kill -KILL "$GUNICORN_PID" 2>/dev/null || true
        fi
        
        RESTART_COUNT=$((RESTART_COUNT + 1))
        
        if [ $RESTART_COUNT -lt $MAX_RESTARTS ]; then
            log_message "Restarting in $RESTART_DELAY seconds..."
            sleep $RESTART_DELAY
        fi
    done
    
    log_message "Maximum restart attempts ($MAX_RESTARTS) reached. Exiting."
    exit 1
}

# Set up signal handlers
trap cleanup SIGTERM SIGINT SIGQUIT

# Check the DEBUG environment variable
if [ "$DEBUG" = "true" ] || [ "$DEBUG" = "1" ] || [ "$DEBUG" = "t" ]; then
    start_gunicorn "/app/scripts/gunicorn-dev.py" "development"
else
    # Use quiet configuration if QUIET_MODE is set
    if [ "$QUIET_MODE" = "true" ] || [ "$QUIET_MODE" = "1" ]; then
        log_message "Using quiet Gunicorn configuration (suppressing connection errors)"
        start_gunicorn "/app/scripts/gunicorn_quiet.py" "production (quiet)"
    else
        start_gunicorn "/app/scripts/gunicorn.py" "production"
    fi
fi
