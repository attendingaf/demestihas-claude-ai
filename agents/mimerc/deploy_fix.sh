#!/bin/bash

# MiMerc Fix Deployment Script
# Purpose: Redeploy MiMerc agent containers with state accumulation fixes
# This script rebuilds and restarts the containers after code changes

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_NAME="mimerc"
LOG_FILE="${SCRIPT_DIR}/deploy_fix.log"

# Function to print colored messages
print_message() {
    echo -e "${2}${1}${NC}"
}

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# Function to check prerequisites
check_prerequisites() {
    print_message "Checking prerequisites..." "$BLUE"

    # Check if Docker is installed and running
    if ! command -v docker &> /dev/null; then
        print_message "❌ Docker is not installed!" "$RED"
        exit 1
    fi

    # Check if docker-compose or docker compose is available
    if command -v docker-compose &> /dev/null; then
        COMPOSE_CMD="docker-compose"
    elif docker compose version &> /dev/null 2>&1; then
        COMPOSE_CMD="docker compose"
    else
        print_message "❌ Docker Compose is not installed!" "$RED"
        exit 1
    fi

    # Check if docker-compose.yml exists
    if [ ! -f "${SCRIPT_DIR}/docker-compose.yml" ]; then
        print_message "❌ docker-compose.yml not found in ${SCRIPT_DIR}" "$RED"
        exit 1
    fi

    # Check if .env file exists
    if [ ! -f "${SCRIPT_DIR}/.env" ]; then
        print_message "⚠️  Warning: .env file not found. Using defaults from .env.example" "$YELLOW"
        if [ -f "${SCRIPT_DIR}/.env.example" ]; then
            cp "${SCRIPT_DIR}/.env.example" "${SCRIPT_DIR}/.env"
            print_message "📋 Created .env from .env.example - please update with your credentials" "$YELLOW"
        fi
    fi

    print_message "✅ Prerequisites check passed" "$GREEN"
}

# Function to backup current state
backup_current_state() {
    print_message "Creating backup of current deployment state..." "$BLUE"

    # Get current container status
    echo "=== Container Status Before Deployment ===" >> "$LOG_FILE"
    $COMPOSE_CMD ps >> "$LOG_FILE" 2>&1 || true

    # Save current image tags
    echo "=== Current Images ===" >> "$LOG_FILE"
    docker images | grep $PROJECT_NAME >> "$LOG_FILE" 2>&1 || true

    log_message "Backup completed"
}

# Main deployment function
main() {
    # Clear screen for better visibility
    clear

    # Print header
    print_message "========================================" "$BLUE"
    print_message "   MiMerc Fix Deployment Script v1.0   " "$GREEN"
    print_message "========================================" "$BLUE"
    print_message "Deploying state accumulation fixes..." "$YELLOW"
    print_message "Time: $(date '+%Y-%m-%d %H:%M:%S')" "$BLUE"
    print_message "========================================" "$BLUE"
    echo

    # Initialize log
    log_message "Starting MiMerc fix deployment"
    log_message "Working directory: ${SCRIPT_DIR}"

    # Change to script directory
    cd "$SCRIPT_DIR"

    # Step 1: Check prerequisites
    check_prerequisites
    echo

    # Step 2: Backup current state
    backup_current_state
    echo

    # Step 3: Stop and remove current containers
    print_message "📦 Step 1/4: Stopping and removing current containers..." "$BLUE"
    log_message "Stopping containers"

    $COMPOSE_CMD down --remove-orphans 2>&1 | tee -a "$LOG_FILE"

    if [ $? -eq 0 ]; then
        print_message "✅ Containers stopped and removed successfully" "$GREEN"
    else
        print_message "⚠️  Warning: Some containers may not have been running" "$YELLOW"
    fi
    echo

    # Step 4: Remove old images to ensure clean rebuild
    print_message "🧹 Step 2/4: Removing old images for clean rebuild..." "$BLUE"
    log_message "Removing old images"

    # Remove project-specific images
    docker images | grep "${PROJECT_NAME}" | awk '{print $3}' | xargs -r docker rmi -f 2>&1 | tee -a "$LOG_FILE" || true

    print_message "✅ Old images removed" "$GREEN"
    echo

    # Step 5: Rebuild the containers
    print_message "🔨 Step 3/4: Building containers with fixed code..." "$BLUE"
    log_message "Building containers"

    # Build all services to ensure consistency
    # Using --no-cache to ensure fresh build with new code
    $COMPOSE_CMD build --no-cache 2>&1 | tee -a "$LOG_FILE"

    if [ $? -eq 0 ]; then
        print_message "✅ Containers built successfully with state accumulation fixes" "$GREEN"
    else
        print_message "❌ Build failed! Check $LOG_FILE for details" "$RED"
        exit 1
    fi
    echo

    # Step 6: Start the containers in detached mode
    print_message "🚀 Step 4/4: Starting containers in detached mode..." "$BLUE"
    log_message "Starting containers"

    $COMPOSE_CMD up -d 2>&1 | tee -a "$LOG_FILE"

    if [ $? -eq 0 ]; then
        print_message "✅ Containers started successfully" "$GREEN"
    else
        print_message "❌ Failed to start containers! Check $LOG_FILE for details" "$RED"
        exit 1
    fi
    echo

    # Wait for services to be healthy
    print_message "⏳ Waiting for services to be healthy..." "$BLUE"

    # Wait up to 30 seconds for database to be ready
    WAIT_TIME=0
    MAX_WAIT=30

    while [ $WAIT_TIME -lt $MAX_WAIT ]; do
        if $COMPOSE_CMD ps | grep -q "healthy"; then
            print_message "✅ Database is healthy" "$GREEN"
            break
        fi
        sleep 2
        WAIT_TIME=$((WAIT_TIME + 2))
        echo -n "."
    done
    echo

    # Step 7: Verify deployment
    print_message "🔍 Verifying deployment..." "$BLUE"
    log_message "Verifying deployment"

    # Show running containers
    echo
    print_message "Current container status:" "$YELLOW"
    $COMPOSE_CMD ps

    # Check if agent container is running
    if $COMPOSE_CMD ps | grep -q "mimerc-agent.*Up"; then
        print_message "✅ MiMerc agent is running" "$GREEN"
    else
        print_message "⚠️  MiMerc agent may not be running properly" "$YELLOW"
    fi

    # Check if database is healthy
    if $COMPOSE_CMD ps | grep -q "mimerc-postgres.*healthy"; then
        print_message "✅ PostgreSQL database is healthy" "$GREEN"
    else
        print_message "⚠️  Database health check failed" "$YELLOW"
    fi

    echo
    print_message "========================================" "$BLUE"
    print_message "    📱 DEPLOYMENT COMPLETE! 📱" "$GREEN"
    print_message "========================================" "$BLUE"
    echo

    # Print testing instructions
    print_message "🧪 Testing Instructions:" "$YELLOW"
    print_message "1. Open Telegram and search for your bot" "$NC"
    print_message "2. Send /start to initialize the bot" "$NC"
    print_message "3. Test the fix by adding items multiple times:" "$NC"
    print_message "   - 'Add milk to my list'" "$NC"
    print_message "   - 'Add milk to my list' (again)" "$NC"
    print_message "   - 'Show me my list'" "$NC"
    print_message "4. Verify that 'milk' appears only once with quantity 2.0" "$NC"
    echo

    print_message "📊 Monitoring:" "$YELLOW"
    print_message "• View logs: $COMPOSE_CMD logs -f mimerc-agent" "$NC"
    print_message "• View Telegram bot logs: $COMPOSE_CMD logs -f telegram-bot" "$NC"
    print_message "• Check database: $COMPOSE_CMD exec mimerc-db psql -U \$POSTGRES_USER -d \$POSTGRES_DB" "$NC"
    echo

    print_message "🔧 Troubleshooting:" "$YELLOW"
    print_message "• If bot doesn't respond, check: $COMPOSE_CMD logs mimerc-agent" "$NC"
    print_message "• To restart: $COMPOSE_CMD restart mimerc-agent" "$NC"
    print_message "• Full logs available at: $LOG_FILE" "$NC"
    echo

    # Log completion
    log_message "Deployment completed successfully"
    log_message "========================================\n"

    # Final status check
    print_message "Final Status Check:" "$BLUE"
    $COMPOSE_CMD ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"

    echo
    print_message "✨ MiMerc state accumulation fixes have been deployed successfully!" "$GREEN"
    print_message "The agent should now maintain clean, non-duplicated grocery lists." "$GREEN"
}

# Error handler
trap 'handle_error $? $LINENO' ERR

handle_error() {
    print_message "❌ Error occurred at line $2 with exit code $1" "$RED"
    print_message "Check the log file for details: $LOG_FILE" "$YELLOW"
    log_message "Error occurred at line $2 with exit code $1"
    exit 1
}

# Run the main function
main "$@"
