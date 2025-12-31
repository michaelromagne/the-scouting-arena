#!/bin/bash

# Stop the running ETL process and all its children

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PID_FILE="$PROJECT_ROOT/logs/etl.pid"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "🛑 Stopping ETL process..."
echo ""

if [[ ! -f "$PID_FILE" ]]; then
    echo -e "${YELLOW}⚠️  No PID file found${NC}"
    echo "Looking for any running ETL processes..."

    # Find any running ETL processes
    PIDS=$(ps aux | grep -E "(weekly_update|remote_etl|player_stats)" | grep -v grep | awk '{print $2}')

    if [[ -z "$PIDS" ]]; then
        echo -e "${GREEN}✓ No ETL processes running${NC}"
        exit 0
    else
        echo "Found ETL processes: $PIDS"
        echo "Killing them..."
        kill $PIDS 2>/dev/null || true
        sleep 1

        # Force kill if still running
        for pid in $PIDS; do
            if ps -p $pid > /dev/null 2>&1; then
                echo "Force killing $pid..."
                kill -9 $pid 2>/dev/null || true
            fi
        done

        echo -e "${GREEN}✓ Stopped all ETL processes${NC}"
        exit 0
    fi
fi

# Get the main PID
MAIN_PID=$(cat "$PID_FILE")

echo "Main process PID: $MAIN_PID"

# Check if main process is running
if ! ps -p "$MAIN_PID" > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Main process $MAIN_PID is not running${NC}"
    rm -f "$PID_FILE"

    # But check for orphaned child processes
    ORPHANS=$(ps aux | grep -E "(weekly_update|remote_etl|player_stats)" | grep -v grep | awk '{print $2}')
    if [[ -n "$ORPHANS" ]]; then
        echo "Found orphaned ETL processes: $ORPHANS"
        echo "Killing them..."
        kill $ORPHANS 2>/dev/null || true
    fi

    echo -e "${GREEN}✓ Cleanup complete${NC}"
    exit 0
fi

# Find all child processes
echo "Finding child processes..."
CHILD_PIDS=$(pgrep -P $MAIN_PID 2>/dev/null || true)

# Also find any related processes by name
RELATED_PIDS=$(ps aux | grep -E "(remote_etl|player_stats)" | grep -v grep | awk '{print $2}')

# Combine all PIDs (main + children + related)
ALL_PIDS="$MAIN_PID"
if [[ -n "$CHILD_PIDS" ]]; then
    ALL_PIDS="$ALL_PIDS $CHILD_PIDS"
fi
if [[ -n "$RELATED_PIDS" ]]; then
    ALL_PIDS="$ALL_PIDS $RELATED_PIDS"
fi

# Remove duplicates
ALL_PIDS=$(echo "$ALL_PIDS" | tr ' ' '\n' | sort -u | tr '\n' ' ')

echo "Processes to kill: $ALL_PIDS"
echo ""

# Kill gracefully first
echo "Sending TERM signal..."
kill $ALL_PIDS 2>/dev/null || true
sleep 2

# Check if any are still running
STILL_RUNNING=""
for pid in $ALL_PIDS; do
    if ps -p $pid > /dev/null 2>&1; then
        STILL_RUNNING="$STILL_RUNNING $pid"
    fi
done

# Force kill if needed
if [[ -n "$STILL_RUNNING" ]]; then
    echo "Force killing remaining processes: $STILL_RUNNING"
    kill -9 $STILL_RUNNING 2>/dev/null || true
    sleep 1
fi

# Clean up PID file
rm -f "$PID_FILE"

echo ""
echo -e "${GREEN}✓ ETL process stopped successfully${NC}"

# Show last log lines
LATEST_LOG=$(ls -t "$PROJECT_ROOT/logs/etl_"*.log 2>/dev/null | head -1 || echo "")
if [[ -n "$LATEST_LOG" ]]; then
    echo ""
    echo "Last log file: $LATEST_LOG"
    echo "Last 10 lines:"
    echo "---"
    tail -10 "$LATEST_LOG" | sed 's/^/  /'
    echo "---"
fi
