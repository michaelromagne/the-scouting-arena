#!/bin/bash

# Run the ETL pipeline in background
# This script starts the ETL process in the background and logs output to a file
#
# Usage:
#   ./scripts/run_etl_background.sh [SEASONS] [LEAGUES] [FBREF_CHECKPOINT] [TM_CHECKPOINT] [TM_URLS] [TEAMS_FBREF_CHECKPOINT]
#
# Examples:
#   # Full extraction + load (default) - extracts both players and teams
#   ./scripts/run_etl_background.sh "2425,2526" "All"
#
#   # Resume from checkpoint files
#   ./scripts/run_etl_background.sh "2425,2526" "All" \
#     "data/players_fbref_stats_raw_*.csv" \
#     "data/transfermarkt_checkpoint_*.csv" \
#     "data/transfermarkt_club_urls.json" \
#     "data/teams_fbref_stats_raw_*.csv"

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$PROJECT_ROOT/logs/etl_${TIMESTAMP}.log"
PID_FILE="$PROJECT_ROOT/logs/etl.pid"

# Assign positional arguments
SEASONS="${1:-2425,2526}"
LEAGUES="${2:-All}"
FBREF_CHECKPOINT_FILE="${3:-}"
TRANSFERMARKT_CHECKPOINT_FILE="${4:-}"
TRANSFERMARKT_CLUB_URLS_FILE="${5:-}"
TEAMS_FBREF_CHECKPOINT_FILE="${6:-}"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Create logs directory if it doesn't exist
mkdir -p "$PROJECT_ROOT/logs"

# Check if ETL is already running
if [[ -f "$PID_FILE" ]]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  ETL process is already running (PID: $OLD_PID)${NC}"
        echo -e "${YELLOW}   Log file: $(ls -t $PROJECT_ROOT/logs/etl_*.log | head -1)${NC}"
        echo ""
        echo "To view logs in real-time:"
        echo "  tail -f $(ls -t $PROJECT_ROOT/logs/etl_*.log | head -1)"
        echo ""
        echo "To stop the running process:"
        echo "  kill $OLD_PID"
        exit 1
    else
        # Old PID file exists but process is not running
        rm -f "$PID_FILE"
    fi
fi

echo -e "${BLUE}🚀 Starting ETL pipeline in background (Players + Teams)...${NC}"
echo -e "${BLUE}   Seasons: $SEASONS${NC}"
echo -e "${BLUE}   Leagues: $LEAGUES${NC}"
echo -e "${BLUE}   Log file: $LOG_FILE${NC}"
if [[ -n "$FBREF_CHECKPOINT_FILE" ]]; then
    echo -e "${BLUE}   Players FBref checkpoint: $FBREF_CHECKPOINT_FILE${NC}"
fi
if [[ -n "$TRANSFERMARKT_CHECKPOINT_FILE" ]]; then
    echo -e "${BLUE}   Transfermarkt checkpoint: $TRANSFERMARKT_CHECKPOINT_FILE${NC}"
fi
if [[ -n "$TRANSFERMARKT_CLUB_URLS_FILE" ]]; then
    echo -e "${BLUE}   Club URLs file: $TRANSFERMARKT_CLUB_URLS_FILE${NC}"
fi
if [[ -n "$TEAMS_FBREF_CHECKPOINT_FILE" ]]; then
    echo -e "${BLUE}   Teams FBref checkpoint: $TEAMS_FBREF_CHECKPOINT_FILE${NC}"
fi
echo ""

# Check if DATABASE_URL is set
if [[ -z "${DATABASE_URL:-}" ]]; then
    echo -e "${YELLOW}⚠️  DATABASE_URL not set${NC}"
    echo "Please set it first, for example:"
    echo "  export DATABASE_URL='postgresql://...' "
    echo ""
    echo "Or run with it inline:"
    echo "  DATABASE_URL='postgresql://...' ./scripts/run_etl_background.sh"
    exit 1
fi

# Build the command with optional arguments
CMD_ARGS=(
    "python" "scripts/remote_etl_pipeline.py"
    "--seasons" "$SEASONS"
    "--leagues" "$LEAGUES"
    "--data-dir" "data"
)

if [[ -n "$FBREF_CHECKPOINT_FILE" ]]; then
    CMD_ARGS+=("--fbref-checkpoint-file" "$FBREF_CHECKPOINT_FILE")
fi
if [[ -n "$TRANSFERMARKT_CHECKPOINT_FILE" ]]; then
    CMD_ARGS+=("--transfermarkt-checkpoint-file" "$TRANSFERMARKT_CHECKPOINT_FILE")
fi
if [[ -n "$TRANSFERMARKT_CLUB_URLS_FILE" ]]; then
    CMD_ARGS+=("--transfermarkt-club-urls-file" "$TRANSFERMARKT_CLUB_URLS_FILE")
fi
if [[ -n "$TEAMS_FBREF_CHECKPOINT_FILE" ]]; then
    CMD_ARGS+=("--teams-fbref-checkpoint-file" "$TEAMS_FBREF_CHECKPOINT_FILE")
fi

# Run the pipeline in background
cd "$PROJECT_ROOT"
nohup poetry run "${CMD_ARGS[@]}" > "$LOG_FILE" 2>&1 &

# Save the PID
ETL_PID=$!
echo "$ETL_PID" > "$PID_FILE"

echo -e "${GREEN}✓ ETL process started (PID: $ETL_PID)${NC}"
echo ""
echo "To view logs in real-time:"
echo -e "${GREEN}  tail -f $LOG_FILE${NC}"
echo ""
echo "To check if the process is still running:"
echo -e "${GREEN}  ps -p $ETL_PID${NC}"
echo ""
echo "Or use the status script:"
echo -e "${GREEN}  ./scripts/check_etl_status.sh${NC}"
echo ""
echo "To stop the process:"
echo -e "${GREEN}  kill $ETL_PID${NC}"
echo ""
echo "The process will continue running even if you close this terminal."
echo "Data will be saved to: $PROJECT_ROOT/data/"
