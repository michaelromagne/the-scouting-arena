#!/bin/bash

# Check the status of the background ETL process

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PID_FILE="$PROJECT_ROOT/logs/etl.pid"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🔍 Checking ETL process status...${NC}"
echo ""

if [[ ! -f "$PID_FILE" ]]; then
    echo -e "${YELLOW}⚠️  No ETL process PID file found${NC}"
    echo "   The ETL is not currently running (or was never started)"
    exit 0
fi

ETL_PID=$(cat "$PID_FILE")

if ps -p "$ETL_PID" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ ETL process is running (PID: $ETL_PID)${NC}"

    # Get process runtime
    RUNTIME=$(ps -p "$ETL_PID" -o etime= | tr -d ' ')
    echo -e "${BLUE}⏱️  Runtime: $RUNTIME${NC}"

    # Get the latest log file
    LATEST_LOG=$(ls -t "$PROJECT_ROOT/logs/etl_"*.log 2>/dev/null | head -1 || echo "")
    SOCCERDATA_INFO_LOG="$HOME/soccerdata/logs/info.log"
    SOCCERDATA_ERROR_LOG="$HOME/soccerdata/logs/error.log"

    if [[ -n "$LATEST_LOG" ]]; then
        echo ""
        echo -e "${BLUE}📄 Main ETL Log:${NC} $LATEST_LOG"
        LOG_MODIFIED=$(stat -f "%Sm" "$LATEST_LOG" 2>/dev/null || echo "unknown")
        echo "   Last modified: $LOG_MODIFIED"
        echo ""
        echo "Last 20 lines:"
        echo "---"
        tail -20 "$LATEST_LOG" | sed 's/^/  /'
        echo "---"
    fi

    # Check soccerdata logs (where actual scraping activity is logged)
    if [[ -f "$SOCCERDATA_INFO_LOG" ]]; then
        echo ""
        echo -e "${BLUE}🌐 FBref Scraping Activity:${NC} $SOCCERDATA_INFO_LOG"
        INFO_MODIFIED=$(stat -f "%Sm" "$SOCCERDATA_INFO_LOG" 2>/dev/null || echo "unknown")
        echo "   Last modified: $INFO_MODIFIED"
        echo ""
        echo "Recent scraping progress:"
        echo "---"
        grep "Successfully extracted category" "$SOCCERDATA_INFO_LOG" 2>/dev/null | tail -10 | sed 's/^/  /' || echo "  No extraction logs found"
        echo "---"
        echo ""
        echo "Last 15 lines of activity:"
        echo "---"
        tail -15 "$SOCCERDATA_INFO_LOG" | sed 's/^/  /'
        echo "---"
    fi

    # Check for recent errors
    if [[ -f "$SOCCERDATA_ERROR_LOG" ]]; then
        RECENT_ERRORS=$(tail -20 "$SOCCERDATA_ERROR_LOG" 2>/dev/null | grep "$(date '+%Y-%m-%d')" || echo "")
        if [[ -n "$RECENT_ERRORS" ]]; then
            echo ""
            echo -e "${YELLOW}⚠️  Recent errors today:${NC}"
            echo "---"
            echo "$RECENT_ERRORS" | sed 's/^/  /'
            echo "---"
        fi
    fi

    echo ""
    echo -e "${BLUE}📊 To monitor logs in real-time:${NC}"
    if [[ -n "$LATEST_LOG" ]]; then
        echo -e "${GREEN}  Main ETL:      tail -f $LATEST_LOG${NC}"
    fi
    if [[ -f "$SOCCERDATA_INFO_LOG" ]]; then
        echo -e "${GREEN}  FBref scraper: tail -f $SOCCERDATA_INFO_LOG${NC}"
    fi
    echo ""
    echo "To stop the process:"
    echo -e "${GREEN}  kill $ETL_PID${NC}"
else
    echo -e "${RED}✗ ETL process is not running${NC}"
    echo "   PID file exists but process $ETL_PID is not active"

    # Clean up stale PID file
    rm -f "$PID_FILE"

    # Show latest log file
    LATEST_LOG=$(ls -t "$PROJECT_ROOT/logs/etl_"*.log 2>/dev/null | head -1 || echo "")
    if [[ -n "$LATEST_LOG" ]]; then
        echo ""
        echo "Last log file: $LATEST_LOG"
        echo ""
        echo "Last 30 lines (may show why it stopped):"
        echo "---"
        tail -30 "$LATEST_LOG" | sed 's/^/  /'
        echo "---"
    fi
fi
