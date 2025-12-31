# Data Extraction (Legacy)

⚠️ **Note**: This module is legacy. For new data loading, use `scouting.etl.load_from_csv` instead.

This module handles the extraction and processing of football player statistics from FBref and Transfermarkt.

## Data Sources

- **FBref**: Provides detailed player statistics (goals, assists, passes, etc.)
- **Transfermarkt**: Provides player market values

## Extraction Process

The data extraction is handled by the `player_stats.py` script, which can be run from the command line:

```bash
python -m scouting.data_transform.player_stats --seasons 2425 --leagues All --no-cache --output-dir data
```

### Command Line Options

- `--seasons`: Comma-separated list of seasons to extract (e.g. '2223,2324,2425')
- `--leagues`: Comma-separated list of leagues to extract or 'All' for all configured leagues
- `--no-cache`: Set to True if you want to extract new data and avoid cache
- `--output-dir`: Directory to save output files (default: 'data')
- `--checkpoint-file`: Path to checkpoint file for Transfermarkt scraping (default: 'transfermarkt_checkpoint.csv')

### Output Files

The script generates these output files:
1. `data/players_fbref_stats_raw.csv`: Raw FBref statistics (intermediate file)
2. `data/players_identity.csv`: Core player information (name, team, league, season, position, etc.)
3. `data/players_metrics.csv`: Statistical performance metrics with joining keys
4. `data/players_transfermarkt.csv`: Market values and images (when available)

The separate CSV files support modular ETL processing - use them individually with `load_from_csv.py` or combine them programmatically using `load_combined_player_data()` function.

## Modern Alternative

For new projects, use the modern ETL pipeline:

```bash
# Load any CSV/Excel file into the database
poetry run python -m scouting.etl.load_from_csv your_data.csv --materialize

# Then use the web interface or API for analysis
# Frontend: http://localhost:3000
# API: http://localhost:8000/docs
```

## Legacy Analysis

The notebook `notebooks/4_scouting_with_fbref.ipynb` contains examples of:
- Data loading and exploration
- Statistical analysis
- Player clustering
- Performance metrics calculation
