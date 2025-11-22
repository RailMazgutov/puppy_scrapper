#!/bin/bash
#
# Web Page Monitor - Cron Runner Script
# This script is designed to be executed by cron to monitor URLs for changes.
#
# Usage:
#   ./run_monitor.sh                    # Run with default settings
#   ./run_monitor.sh /path/to/urls.txt  # Run with custom URL file
#

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Change to script directory
cd "$SCRIPT_DIR" || exit 1

# URL file (optional first argument)
URL_FILE="${1:-}"

# Log file for cron output
CRON_LOG="$SCRIPT_DIR/cron.log"

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$CRON_LOG"
}

log "Starting web monitor cron job"

# Check if virtual environment exists and activate it
if [ -d "$SCRIPT_DIR/venv" ]; then
    source "$SCRIPT_DIR/venv/bin/activate"
    log "Activated virtual environment"
elif [ -d "$SCRIPT_DIR/.venv" ]; then
    source "$SCRIPT_DIR/.venv/bin/activate"
    log "Activated virtual environment"
fi

# Build the command
CMD="python3 $SCRIPT_DIR/web_monitor.py --cron"

# Add custom URL file if provided
if [ -n "$URL_FILE" ]; then
    CMD="$CMD -f $URL_FILE"
fi

# Run the monitor
log "Executing: $CMD"
$CMD 2>> "$CRON_LOG"
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    log "Web monitor completed successfully"
else
    log "Web monitor failed with exit code: $EXIT_CODE"
fi

# Deactivate virtual environment if it was activated
if [ -n "$VIRTUAL_ENV" ]; then
    deactivate 2>/dev/null
fi

exit $EXIT_CODE
