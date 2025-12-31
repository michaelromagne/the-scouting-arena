## Scouting API

Minimal FastAPI service exposing data and Plotly JSON.

### Quickstart (Docker - Recommended)

1) Start backend services (Database, Redis, API):
```bash
docker-compose up -d --build db redis api
```

2) Load sample data:
```bash
poetry run python -m scouting.etl.load_from_csv data/short_example_data.csv --materialize
```

3) Open API documentation:
```bash
http://127.0.0.1:8000/docs
```

### Local Development (Alternative)

1) Start only database and Redis (for local API development):
```bash
docker-compose up -d db redis
```

2) Set environment and install dependencies:
```bash
export DATABASE_URL=postgresql+psycopg://scout:scout@localhost:5432/scouting
poetry install --no-interaction
```

3) Run API locally with hot reload:
```bash
poetry run uvicorn scouting.api.main:app --reload --port 8000 --log-level info
```

### Full Stack Development

To run the complete application (API + Frontend):

1) Start backend services:
```bash
docker-compose up -d --build db redis api
```

2) Start frontend (in separate terminal):
```bash
cd web
npm install
npm run dev
```

3) Access applications:
- Frontend: http://localhost:3000
- API docs: http://localhost:8000/docs

Use env file to override defaults (copy to `.env` at repo root):
```
POSTGRES_DB=scouting
POSTGRES_USER=scout
POSTGRES_PASSWORD=scout
DATABASE_URL=postgresql+psycopg://scout:scout@db:5432/scouting
CORS_ALLOW_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
CORS_ALLOW_METHODS=GET,POST,OPTIONS
CORS_ALLOW_HEADERS=Authorization,Content-Type,Accept,Origin
CORS_ALLOW_CREDENTIALS=false
REDIS_URL=redis://redis:6379/0
CACHE_TTL_SECONDS=300
CACHE_PREFIX=scouting:api:
```

API available at `http://localhost:8000`.

### Database migrations (Alembic)

Initialize DB schema or apply changes safely:
```
export DATABASE_URL=postgresql+psycopg://scout:scout@localhost:5432/scouting
alembic upgrade head
```

Create a new migration after model changes:
```
alembic revision --autogenerate -m "your message"
alembic upgrade head
```

Baseline an existing DB (only if needed):
```
alembic stamp head
```

### CORS configuration

The API enables CORS with safe defaults for local frontends. Configure via env vars:

- `CORS_ALLOW_ORIGINS`: comma-separated list of origins.
  - Default: `http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173`
- `CORS_ALLOW_METHODS`: allowed methods (default: `GET,POST,OPTIONS`).
- `CORS_ALLOW_HEADERS`: allowed headers (default: `Authorization,Content-Type,Accept,Origin`).
- `CORS_ALLOW_CREDENTIALS`: `true|false` (default: `false`). Disabled if `*` origins are used.

Examples:
```
export CORS_ALLOW_ORIGINS="http://localhost:3000,http://127.0.0.1:3000"
export CORS_ALLOW_METHODS="GET,POST,OPTIONS"
export CORS_ALLOW_HEADERS="Authorization,Content-Type,Accept,Origin"
export CORS_ALLOW_CREDENTIALS="false"
```

### Caching

- Memory cache enabled by default.
- Optional Redis via `REDIS_URL`; JSON payloads and Plotly figures are cached.
- TTL default is 300 seconds, configurable via `CACHE_TTL_SECONDS`.
- Keys are derived from query params so distinct requests are cached independently.

Env vars:
```
export REDIS_URL="redis://localhost:6379/0"   # optional
export CACHE_PREFIX="scouting:api:"
export CACHE_TTL_SECONDS="300"
```

### Switch to production Redis

- Use a managed Redis (e.g., AWS ElastiCache). Obtain the primary endpoint and port.
- Set `REDIS_URL` to your managed instance (no schema changes needed):
```
export REDIS_URL="redis://<elasticache-endpoint>:6379/0"
export CACHE_TTL_SECONDS=600
export CACHE_PREFIX="scouting:api:"
```
- Run multiple API workers/containers pointing to the same `REDIS_URL` to share cache.
- Keep `DATABASE_URL` pointing to your RDS instance for full prod parity.

### Helpful errors (metric suggestions)

If a metric code isn't found in `/rankings`, `/scatter`, or chart endpoints, the API returns suggestions based on close matches to known metric codes.

### Endpoints and examples

#### Health
```
curl http://127.0.0.1:8000/health
```

#### Metrics (list/SEARCH)
```
# List first 50
curl 'http://127.0.0.1:8000/metrics'

# Search by text (e.g., pass/shoot/xg) and increase limit
curl -G 'http://127.0.0.1:8000/metrics' --data-urlencode 'q=pass' --data-urlencode 'limit=200'
```

#### Players (search and filter)
```
# Basic search (ilike on player name). Encodes spaces/UTF-8 automatically.
curl -G 'http://127.0.0.1:8000/players' --data-urlencode 'q=Moussa Niakhate'

# Filter by league with space
curl -G 'http://127.0.0.1:8000/players' --data-urlencode 'league=FRA-Ligue 1' --data-urlencode 'limit=20'

# Season accepts short (2425) or long (2024-2025)
curl -G 'http://127.0.0.1:8000/players' --data-urlencode 'q=Arnautovi' --data-urlencode 'season=2425' --data-urlencode 'league=ITA-Serie A'
curl -G 'http://127.0.0.1:8000/players' --data-urlencode 'q=Arnautovi' --data-urlencode 'season=2024-2025'
```

#### Player image (Transfermarkt image URL if present)
```
# Get DB id first
curl -G 'http://127.0.0.1:8000/players' --data-urlencode 'q=Arnautovi' --data-urlencode 'limit=1'

# Then fetch image by DB id
curl 'http://127.0.0.1:8000/players/3/image'
```

#### Player details (all metrics for a season)
```
# Latest season for the player
curl 'http://127.0.0.1:8000/players/3'

# Explicit season (accepts 2425 or 2024-2025)
curl -G 'http://127.0.0.1:8000/players/3' --data-urlencode 'season=2425'
```

#### Rankings (data)
```
# Top-N by metric with filters (default min_minutes=0). Use 0 for sample data.
curl -G 'http://127.0.0.1:8000/rankings' \
  --data-urlencode 'metric=expected_xg_per_90' \
  --data-urlencode 'season=2425' \
  --data-urlencode 'min_minutes=0' \
  --data-urlencode 'limit=10'
```

#### Scatter (data)
```
# 2D points for two metrics, with filters
curl -G 'http://127.0.0.1:8000/scatter' \
  --data-urlencode 'x=expected_xg_per_90' \
  --data-urlencode 'y=standard_sot_per_90' \
  --data-urlencode 'season=2425' \
  --data-urlencode 'min_minutes=0' \
  --data-urlencode 'limit=500'
```

#### Chart: Rankings bar (Plotly JSON)
```
curl -G 'http://127.0.0.1:8000/charts/rankings/bar' \
  --data-urlencode 'metric=shooting' \
  --data-urlencode 'season=2425' \
  --data-urlencode 'min_minutes=0' \
  --data-urlencode 'limit=10'
```

#### Chart: Scatter metrics (Plotly JSON)
```
curl -G 'http://127.0.0.1:8000/charts/scatter/metrics' \
  --data-urlencode 'x=shooting' \
  --data-urlencode 'y=passing' \
  --data-urlencode 'season=2425' \
  --data-urlencode 'min_minutes=0' \
  --data-urlencode 'limit=200'
```

### Notes
- Season normalization supports 2425 and 2024-2025.
- For small samples with low minutes, pass `min_minutes=0`.
- Use `/metrics` to discover available metric codes.
