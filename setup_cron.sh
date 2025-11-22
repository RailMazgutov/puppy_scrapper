#!/bin/bash
#
# Web Page Monitor - Cron Setup Script
# This script helps install or remove the hourly cron job.
#
# Usage:
#   ./setup_cron.sh install    # Install the cron job (runs every hour)
#   ./setup_cron.sh remove     # Remove the cron job
#   ./setup_cron.sh status     # Check if cron job is installed
#

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNER_SCRIPT="$SCRIPT_DIR/run_monitor.sh"

# Cron job identifier comment (used to find/manage our cron entry)
CRON_ID="# web-page-monitor-cron"

# Cron schedule: runs every hour at minute 0
CRON_SCHEDULE="0 * * * *"

# Full cron entry
CRON_ENTRY="$CRON_SCHEDULE $RUNNER_SCRIPT $CRON_ID"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_success() {
    echo -e "${GREEN}$1${NC}"
}

print_error() {
    echo -e "${RED}$1${NC}"
}

print_warning() {
    echo -e "${YELLOW}$1${NC}"
}

check_dependencies() {
    # Check if run_monitor.sh exists
    if [ ! -f "$RUNNER_SCRIPT" ]; then
        print_error "Error: run_monitor.sh not found at $RUNNER_SCRIPT"
        exit 1
    fi

    # Check if run_monitor.sh is executable
    if [ ! -x "$RUNNER_SCRIPT" ]; then
        print_warning "Making run_monitor.sh executable..."
        chmod +x "$RUNNER_SCRIPT"
    fi

    # Check if crontab is available
    if ! command -v crontab &> /dev/null; then
        print_error "Error: crontab command not found. Please install cron."
        exit 1
    fi
}

install_cron() {
    check_dependencies

    # Check if already installed
    if crontab -l 2>/dev/null | grep -q "$CRON_ID"; then
        print_warning "Cron job is already installed."
        echo "Use './setup_cron.sh remove' to remove it first if you want to reinstall."
        return 0
    fi

    # Add cron job
    (crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -

    if [ $? -eq 0 ]; then
        print_success "Cron job installed successfully!"
        echo ""
        echo "The web monitor will run every hour at minute 0."
        echo ""
        echo "Cron entry added:"
        echo "  $CRON_ENTRY"
        echo ""
        echo "Configuration:"
        echo "  - URLs file: $SCRIPT_DIR/urls.txt"
        echo "  - Log file:  $SCRIPT_DIR/monitor.log"
        echo "  - Cron log:  $SCRIPT_DIR/cron.log"
        echo ""
        echo "To change the schedule, edit your crontab with: crontab -e"
    else
        print_error "Failed to install cron job"
        exit 1
    fi
}

remove_cron() {
    # Check if cron job exists
    if ! crontab -l 2>/dev/null | grep -q "$CRON_ID"; then
        print_warning "Cron job is not installed."
        return 0
    fi

    # Remove cron job
    crontab -l 2>/dev/null | grep -v "$CRON_ID" | crontab -

    if [ $? -eq 0 ]; then
        print_success "Cron job removed successfully!"
    else
        print_error "Failed to remove cron job"
        exit 1
    fi
}

status_cron() {
    echo "Checking cron job status..."
    echo ""

    if crontab -l 2>/dev/null | grep -q "$CRON_ID"; then
        print_success "Cron job is INSTALLED"
        echo ""
        echo "Current cron entry:"
        crontab -l 2>/dev/null | grep "$CRON_ID"
    else
        print_warning "Cron job is NOT installed"
        echo ""
        echo "Run './setup_cron.sh install' to install it."
    fi
}

show_help() {
    echo "Web Page Monitor - Cron Setup Script"
    echo ""
    echo "Usage: $0 <command>"
    echo ""
    echo "Commands:"
    echo "  install   Install the cron job (runs every hour)"
    echo "  remove    Remove the cron job"
    echo "  status    Check if the cron job is installed"
    echo "  help      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 install    # Set up hourly monitoring"
    echo "  $0 status     # Check if it's running"
    echo "  $0 remove     # Stop the monitoring"
    echo ""
    echo "After installation, edit urls.txt to configure which URLs to monitor."
}

# Main
case "${1:-help}" in
    install)
        install_cron
        ;;
    remove)
        remove_cron
        ;;
    status)
        status_cron
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
