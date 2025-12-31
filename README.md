# The Scouting Arena Application

A football scouting application providing player statistics, similarity analysis, and multi-season comparisons across different competitions. Built with FastAPI, Next.js, and modern data analysis tools.

Website URL : [https://the-scouting-arena.com](https://the-scouting-arena.com)

⚠️ If the website is down (💸), contact me by email at `michael.romagne@gmail.com` or Linkedin if you want to discuss it or want a demo.

## Features

- Player statistics across multiple competitions with per-90 metrics
- Position-based analysis and category scores
- Player similarity system using cosine similarity on standardized metrics
- Multi-season support for historical analysis
- RESTful API with interactive Plotly charts
- Next.js frontend with real-time visualizations
- Automated ETL pipeline with background processing

## Application Preview

<table>
  <tr>
    <td width="50%"><img src="assets/home_page.png" alt="Home Page" /></td>
    <td width="50%"><img src="assets/rankings.png" alt="Rankings" /></td>
  </tr>
  <tr>
    <td width="50%"><img src="assets/scatter_plot.png" alt="Scatter Plot Analysis" /></td>
    <td width="50%"><img src="assets/comparison.png" alt="Player Comparison" /></td>
  </tr>
  <tr>
    <td width="50%"><img src="assets/player_similarity.png" alt="Player Similarity" /></td>
    <td width="50%"><img src="assets/national_teams.png" alt="National Teams" /></td>
  </tr>
</table>

## Prerequisites

- Docker
- Poetry
- PostgreSQL

## Quick Start

### 1. Clone and Setup

```bash
git clone git@github.com:michaelromagne/scouting.git
cd scouting
```

### 2. Start Services

```bash
# Start backend services (Database, Redis, API)
docker-compose up -d --build db redis api
```

### 3. Load Data

**Automated Pipeline (Recommended)**
```bash
# Set database URL
export DATABASE_URL='postgresql://scout:scout@localhost:5432/scouting'

# Full extraction and load
./scripts/run_etl_background.sh "2425,2526" "All"

# Monitor progress
./scripts/check_etl_status.sh

# Resume from checkpoint if interrupted
./scripts/run_etl_background.sh "2425,2526" "All" \
  "data/players_fbref_stats_raw_2425,2526_All_<timestamp>.csv" \
  "data/transfermarkt_checkpoint_2425_<timestamp>.csv" \
  "data/transfermarkt_club_urls.json" \
  "data/teams_fbref_stats_raw_2425,2526_All_<timestamp>.csv"
```

### 4. Start Frontend

```bash
cd web
npm install
npm run dev
```

### 5. Access Applications

- **Frontend**: http://localhost:3000
- **API Documentation**: http://localhost:8000/docs
- **Database**: localhost:5432 (scout/scout)
- **Redis**: localhost:6379

## Development Setup

### Backend Development

```bash
# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -
poetry install

# Start database and Redis only
docker-compose up -d db redis

# Run API locally with hot reload
export DATABASE_URL=postgresql+psycopg://scout:scout@localhost:5432/scouting
poetry run uvicorn scouting.api.main:app --reload --port 8000
```

### Frontend Development

```bash
cd web
npm install
echo "NEXT_PUBLIC_API_URL=http://127.0.0.1:8000" > .env.local
npm run dev
```

## Project Structure

```
scouting/
├── scouting/
│   ├── api/            # FastAPI REST API
│   ├── db/             # Database models
│   ├── etl/            # ETL pipeline
│   └── data_transform/ # Data extraction
├── web/                # Next.js frontend
├── scripts/            # Background ETL scripts
├── alembic/            # Database migrations
└── data/               # Generated CSV files
```

## Architecture

- **Backend**: FastAPI + PostgreSQL + Redis caching
- **Frontend**: Next.js + Tailwind CSS + shadcn/ui
- **Charts**: Interactive Plotly.js visualizations
- **Data**: Tall metrics schema for flexible statistics
- **ETL**: Background processing with checkpoint recovery

## Data Pipeline

### Automated Background Processing

The ETL pipeline runs in the background with checkpoint recovery:

```bash
# Set database URL
export DATABASE_URL='postgresql://scout:scout@localhost:5432/scouting'

# Full extraction and load
./scripts/run_etl_background.sh "2425,2526" "All"

# Monitor progress
./scripts/check_etl_status.sh

# Stop if needed
./scripts/stop_etl.sh
```

### Pipeline Stages

1. **FBRef Extraction**: Player stats from FBRef (270+ minutes filter)
2. **Transfermarkt Enrichment**: Market values and player images
3. **Similarity Computation**: Cosine similarity on standardized per-90 metrics
4. **Database Load**: Bulk insert with retry logic and deduplication

### Generated Files

**Player Data:**
- `players_fbref_stats_raw_*.csv` - FBRef player statistics
- `transfermarkt_checkpoint_*.csv` - Market values and images
- `players_metrics_*.csv` - Processed player metrics for database
- `player_similarities_*.csv` - Pre-computed player similarities

**Team Data:**
- `teams_fbref_stats_raw_*.csv` - FBRef team statistics
- `teams_identity_*.csv` - Team identity data
- `teams_metrics_*.csv` - Processed team metrics for database

### Multi-Season Support

- Season-specific queries: `/players/{id}/similar?season=2425`
- Historical analysis across multiple seasons
- Separate similarity graphs per season

## Player Similarity System

- **Metrics**: Standardized per-90 statistics for fair comparison
- **Algorithm**: Cosine similarity on scaled metrics (StandardScaler)
- **Filtering**: Only players with 270+ minutes played
- **Threshold**: Keeps meaningful similarities (>0.1 score)
- **Storage**: Pre-computed and cached for fast responses

### API Endpoints

```bash
# Get similar players
GET /players/123/similar?season=2425&k=10
GET /players/123/similar?season=2324&k=5
```

## Database Management

### Clean Database

```bash
# Drop and recreate schema
psql -h localhost -U scout -d scouting
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO scout;
GRANT ALL ON SCHEMA public TO public;
\q

# Run migrations and reload data
alembic upgrade head
./scripts/run_etl_background.sh "2425,2526" "All"
```

## Railway PostgreSQL Deployment

### Quick Setup

```bash
# Get Railway database URL from project dashboard
export RAILWAY_DB="postgresql://username:password@host:port/database"

# Apply migrations
DATABASE_URL="$RAILWAY_DB" alembic upgrade head

# Run automated ETL pipeline
DATABASE_URL="$RAILWAY_DB" ./scripts/run_etl_background.sh "2425,2526" "All"

# Monitor progress
./scripts/check_etl_status.sh
```

### Pipeline Features

- **Batch Processing**: Optimized batch sizes for network latency
- **Retry Logic**: Exponential backoff with automatic rollback
- **Idempotent**: Safe to re-run without duplicates
- **Checkpoint Recovery**: Resume from interruptions
- **Deduplication**: Automatic duplicate detection
- **Progress Tracking**: Real-time logging

### Performance

- ~10 minutes for complete multi-season dataset
- 300k+ metrics processed efficiently
- Automatic retry on connection timeouts
- Memory-efficient batch processing

## API Testing

```bash
curl "http://localhost:8000/metrics"
curl "http://localhost:8000/rankings?metric=shooting&season=2425&limit=10"
curl "http://localhost:8000/players/123/similar?season=2425&k=5"
```

## Troubleshooting

**Services:**
- Check status: `docker-compose ps`
- View logs: `docker-compose logs api`
- Restart cache: `docker-compose restart redis`

**ETL:**
- Check status: `./scripts/check_etl_status.sh`
- Stop process: `./scripts/stop_etl.sh`

## Environment Variables

```env
# Database
DATABASE_URL=postgresql+psycopg://scout:scout@localhost:5432/scouting

# API
CORS_ALLOW_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
REDIS_URL=redis://localhost:6379/0

# Frontend
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```
