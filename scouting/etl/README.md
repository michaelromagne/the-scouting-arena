## Database: populate and inspect

Prerequisites
- Docker (for dev DB)
- Poetry (for deps)
- Optional for prod: Terraform, AWS credentials

#### Dev: load data and inspect tables

**Recommended: Use Docker for everything**
```bash
# Start backend services (Database, Redis, API with auto table creation)
docker-compose up -d --build db redis api

# Load sample data
poetry run python -m scouting.etl.load_from_csv data/short_example_data.csv --materialize

# Inspect tables
docker exec -it scouting-db psql -U scout -d scouting -c '\dt'
docker exec -it scouting-db psql -U scout -d scouting -c "SELECT COUNT(*) FROM players;"
docker exec -it scouting-db psql -U scout -d scouting -c "SELECT code, name FROM metric_definitions ORDER BY code LIMIT 20;"
```

**Alternative: Database only (for local API development)**
```bash
# Start only database and Redis
docker-compose up -d db redis

# Set environment and install dependencies
export DATABASE_URL=postgresql+psycopg://scout:scout@localhost:5432/scouting
poetry install --no-interaction

# Load data (creates tables automatically)
poetry run python -m scouting.etl.load_from_csv data/short_example_data.csv --materialize
```

Notes
- The loader auto-detects identity columns (player, team, league, season, pos, minutes/90s) case-insensitively.
- All other numeric columns (excluding section headers like `shooting`, `passing`, etc.) are inserted as metrics.
- Metric codes are normalized (lowercase, `_per_` for `/`, `pct` for `%`, non-alphanumerics collapsed).

#### Prod (AWS RDS): quickstart

1) Deploy Postgres with Terraform
```
cd infra/terraform/postgres
terraform init
terraform apply -auto-approve
```

2) Point the loader to RDS and load your data
```
export DATABASE_URL=postgresql+psycopg://USERNAME:PASSWORD@<rds_endpoint>:5432/scouting
poetry run python -m scouting.etl.load_from_csv <your_excel_or_csv> --materialize
```

3) Inspect RDS (psql or any SQL client)
```
psql "postgresql://USERNAME:PASSWORD@<rds_endpoint>:5432/scouting" -c '\dt'
psql "postgresql://USERNAME:PASSWORD@<rds_endpoint>:5432/scouting" -c 'SELECT COUNT(*) FROM player_metrics;'
```
