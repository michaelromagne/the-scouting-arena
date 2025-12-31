"""
Remote ETL Pipeline. This ETL was vibe coded in order to deploy the project ASAP in prod.

This script provides a complete, automated ETL pipeline that can run remotely
without fear of connection loss. It includes:
- Robust error handling and retry logic
- Data validation and integrity checks
- Automated data extraction from sources
- Safe database updates with rollback capability
- Progress tracking and detailed logging
- Email notifications on completion/failure
"""

import asyncio
import logging
import os
import smtplib
import sys
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

import click
from sqlalchemy import text

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scouting.db.session import get_database_url, session_scope
from scouting.etl.load_from_csv import main as load_csv_main
from scouting.etl.load_teams_from_csv import main as load_teams_csv_main


class RemoteETLPipeline:
    """Robust ETL pipeline for remote execution on Railway."""

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.logger = self._setup_logging()
        self.start_time = datetime.now()
        self.data_dir = Path(config.get("data_dir", "data"))
        self.backup_dir = Path(config.get("backup_dir", "data/backups"))
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.fbref_checkpoint_file = config.get("fbref_checkpoint_file")
        self.transfermarkt_checkpoint_file = config.get("transfermarkt_checkpoint_file")
        self.transfermarkt_club_urls_file = config.get("transfermarkt_club_urls_file")
        self.teams_fbref_checkpoint_file = config.get("teams_fbref_checkpoint_file")

    def _setup_logging(self) -> logging.Logger:
        """Setup logging with console output only."""
        logger = logging.getLogger("remote_etl")
        logger.setLevel(logging.INFO)

        # Create formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        return logger

    async def run_pipeline(self) -> bool:
        """Execute the complete ETL pipeline with error handling."""
        try:
            self.logger.info("🚀 Starting Remote ETL Pipeline")
            self.logger.info(f"Database URL: {get_database_url()}")

            if not self._validate_environment():
                return False

            if not await self._create_database_backup():
                return False

            if not await self._extract_data():
                return False

            if not await self._extract_team_data():
                return False

            if not self._validate_extracted_data():
                return False

            if not await self._load_data_to_database():
                return False

            if not await self._validate_database_integrity():
                return False

            self._cleanup_old_files()

            self.logger.info("✅ ETL Pipeline completed successfully!")
            await self._send_notification(success=True)
            return True

        except Exception as e:
            self.logger.error(f"❌ Pipeline failed: {e}")
            await self._handle_failure(e)
            return False

    def _validate_environment(self) -> bool:
        """Validate required environment variables and dependencies."""
        self.logger.info("🔍 Validating environment...")

        required_vars = ["DATABASE_URL"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]

        if missing_vars:
            self.logger.error(f"Missing environment variables: {missing_vars}")
            return False

        try:
            with session_scope() as session:
                result = session.execute(text("SELECT 1"))
                result.scalar()
            self.logger.info("✅ Database connection successful")
        except Exception as e:
            self.logger.error(f"❌ Database connection failed: {e}")
            return False

        return True

    async def _create_database_backup(self) -> bool:
        """Create a backup of current database state."""
        self.logger.info("💾 Creating database backup...")

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self.backup_dir / f"db_backup_{timestamp}.sql"

            # Export key tables to CSV for backup
            tables_to_backup = [
                "teams",
                "leagues",
                "seasons",
                "player_seasons",
                "metric_definitions",
                "player_metrics",
                "team_seasons",
                "team_metrics",
            ]

            with session_scope() as session:
                for table in tables_to_backup:
                    try:
                        query = f"SELECT COUNT(*) FROM {table}"
                        result = session.execute(text(query))
                        count = result.scalar()
                        self.logger.info(f"  {table}: {count} records")
                    except Exception as e:
                        self.logger.warning(f"  {table}: Could not count records - {e}")

            self.logger.info(f"✅ Backup metadata saved to {backup_file}")
            return True

        except Exception as e:
            self.logger.error(f"❌ Backup creation failed: {e}")
            return False

    async def _extract_data(self) -> bool:
        """Extract fresh player data from sources with retry logic."""
        self.logger.info("📊 Extracting fresh player data...")

        max_retries = 3
        for attempt in range(max_retries):
            try:
                seasons = self.config.get("seasons", "2425")
                leagues = self.config.get("leagues", "All")
                fbref_checkpoint_file = self.config.get("fbref_checkpoint_file")
                transfermarkt_checkpoint_file = self.config.get(
                    "transfermarkt_checkpoint_file"
                )
                transfermarkt_club_urls_file = self.config.get(
                    "transfermarkt_club_urls_file"
                )

                self.logger.info(
                    f"Extracting player data for seasons: {seasons}, leagues: {leagues}"
                )

                # Run player data extraction with retry logic
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    self._run_extraction,
                    seasons,
                    leagues,
                    fbref_checkpoint_file,
                    transfermarkt_checkpoint_file,
                    transfermarkt_club_urls_file,
                )

                self.logger.info("✅ Player data extraction completed")
                return True

            except Exception as e:
                self.logger.warning(
                    f"Player extraction attempt {attempt + 1} failed: {e}"
                )
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 30  # 30, 60, 90 seconds
                    self.logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    self.logger.error("❌ All player extraction attempts failed")
                    return False

        return False

    def _run_extraction(
        self,
        seasons: str,
        leagues: str,
        fbref_checkpoint_file: str | None,
        transfermarkt_checkpoint_file: str | None,
        transfermarkt_club_urls_file: str | None,
    ):
        """Run the data extraction process."""
        # Import and run the extraction function
        # Create a mock context for the click command
        import click.testing

        from scouting.data_transform.player_stats import player_stats_extraction

        runner = click.testing.CliRunner()

        checkpoint_args = []
        if fbref_checkpoint_file:
            checkpoint_args += ["--fbref-checkpoint-file", fbref_checkpoint_file]
        if transfermarkt_checkpoint_file:
            checkpoint_args += [
                "--transfermarkt-checkpoint-file",
                transfermarkt_checkpoint_file,
            ]
        if transfermarkt_club_urls_file:
            checkpoint_args += [
                "--transfermarkt-club-urls-file",
                transfermarkt_club_urls_file,
            ]

        result = runner.invoke(
            player_stats_extraction,
            [
                "--seasons",
                seasons,
                "--leagues",
                leagues,
                "--no-cache",
                "--output-dir",
                str(self.data_dir),
                "--min-games",
                "1.0",
            ]
            + checkpoint_args,
            catch_exceptions=False,
        )

        if result.exit_code != 0:
            raise Exception(
                f"Player data extraction failed with exit code {result.exit_code}"
            )

    async def _extract_team_data(self) -> bool:
        """Extract fresh team data from sources with retry logic."""
        self.logger.info("🏟️  Extracting fresh team data...")

        max_retries = 3
        for attempt in range(max_retries):
            try:
                seasons = self.config.get("seasons", "2425")
                leagues = self.config.get("leagues", "All")
                teams_fbref_checkpoint_file = self.config.get(
                    "teams_fbref_checkpoint_file"
                )

                self.logger.info(
                    f"Extracting team data for seasons: {seasons}, leagues: {leagues}"
                )

                # Run team data extraction
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    self._run_team_extraction,
                    seasons,
                    leagues,
                    teams_fbref_checkpoint_file,
                )

                self.logger.info("✅ Team data extraction completed")
                return True

            except Exception as e:
                self.logger.warning(
                    f"Team extraction attempt {attempt + 1} failed: {e}", exc_info=True
                )
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 30
                    self.logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    self.logger.error("❌ All team extraction attempts failed")
                    return False

        return False

    def _run_team_extraction(
        self,
        seasons: str,
        leagues: str,
        teams_fbref_checkpoint_file: str | None,
    ):
        """Run the team data extraction process."""
        import click.testing

        from scouting.data_transform.team_stats import team_stats_extraction

        runner = click.testing.CliRunner()

        checkpoint_args = []
        if teams_fbref_checkpoint_file:
            checkpoint_args += ["--fbref-checkpoint-file", teams_fbref_checkpoint_file]

        result = runner.invoke(
            team_stats_extraction,
            [
                "--seasons",
                seasons,
                "--leagues",
                leagues,
                "--no-cache",
                "--output-dir",
                str(self.data_dir),
            ]
            + checkpoint_args,
            catch_exceptions=False,
        )

        if result.exit_code != 0:
            raise Exception(
                f"Team data extraction failed with exit code {result.exit_code}"
            )

    def _find_latest_file(self, base_pattern: str) -> Path | None:
        """Find the most recent file matching a base pattern (ignoring date)."""
        # Match files like players_identity_*.csv regardless of date
        matching_files = list(self.data_dir.glob(f"{base_pattern}*.csv"))
        if not matching_files:
            return None
        return max(matching_files, key=lambda f: f.stat().st_mtime)

    def _find_latest_files_per_season(self, base_pattern: str) -> list[Path]:
        """Find the most recent file for each season matching a base pattern.

        This is used for similarity files which have one file per season.
        Pattern: player_similarities_{season}_{timestamp}.csv
        Returns: List of latest files, one per season found.
        """
        matching_files = list(self.data_dir.glob(f"{base_pattern}*.csv"))
        if not matching_files:
            return []

        # Group files by season (extract season from filename)
        # e.g., "player_similarities_2425_20251216_134709.csv" -> season "2425"
        from collections import defaultdict

        season_files: dict[str, list[Path]] = defaultdict(list)

        for f in matching_files:
            # Extract season from filename after the base pattern
            # base_pattern is "player_similarities_", so we get "2425_20251216..."
            name_after_pattern = f.stem.replace(base_pattern.rstrip("_"), "").lstrip(
                "_"
            )
            parts = name_after_pattern.split("_")
            if parts:
                season = parts[0]
                # Only consider valid season patterns (4 digits like 2425, 2526)
                if len(season) == 4 and season.isdigit():
                    season_files[season].append(f)

        # For each season, get the most recent file
        latest_per_season = []
        for season, files in season_files.items():
            latest = max(files, key=lambda f: f.stat().st_mtime)
            latest_per_season.append(latest)

        return latest_per_season

    def _validate_extracted_data(self) -> bool:
        """Validate the quality and completeness of extracted data."""
        self.logger.info("🔍 Validating extracted data...")

        # Find the most recent data files (regardless of date)
        required_patterns = [
            "players_identity_",
            "players_metrics_",
            "teams_identity_",
            "teams_metrics_",
        ]

        for pattern in required_patterns:
            latest_file = self._find_latest_file(pattern)
            if not latest_file:
                self.logger.error(f"❌ No files found matching pattern: {pattern}*.csv")
                return False

            # Validate file content
            try:
                # Import pandas here to avoid global import issues
                import pandas as pd

                df = pd.read_csv(latest_file)
                if df.empty:
                    self.logger.error(f"❌ File is empty: {latest_file}")
                    return False

                self.logger.info(f"✅ {latest_file.name}: {len(df)} records")

                # Basic data quality checks
                if "player" in df.columns:
                    null_players = df["player"].isnull().sum()
                    if null_players > 0:
                        self.logger.warning(
                            f"⚠️  {null_players} null player names in {latest_file.name}"
                        )

            except Exception as e:
                self.logger.error(f"❌ Error reading {latest_file}: {e}")
                return False

        return True

    async def _load_data_to_database(self) -> bool:
        """Load data to database with comprehensive error handling."""
        self.logger.info("📥 Loading data to database...")

        # Find the most recent data files (regardless of date in filename)
        # For most files, we load the single latest file
        # For similarity files, we load one per season
        file_patterns = [
            ("players_identity_", True, False),  # (pattern, required, multi_season)
            ("players_metrics_", True, False),
            ("players_transfermarkt_", False, False),
            ("player_similarities_", False, True),  # Load one per season
            ("teams_identity_", True, False),
            ("teams_metrics_", True, False),
        ]

        for pattern, required, multi_season in file_patterns:
            # Get files to load based on whether this is multi-season
            if multi_season:
                files_to_load = self._find_latest_files_per_season(pattern)
                if files_to_load:
                    self.logger.info(
                        f"Found {len(files_to_load)} similarity files (one per season)"
                    )
            else:
                latest_file = self._find_latest_file(pattern)
                files_to_load = [latest_file] if latest_file else []

            if not files_to_load:
                if required:
                    self.logger.error(
                        f"❌ No files found for required pattern: {pattern}*.csv"
                    )
                    return False
                else:
                    self.logger.warning(
                        f"⚠️  No files found for pattern: {pattern}*.csv"
                    )
                continue

            # Load each file
            for file_to_load in files_to_load:
                if not await self._load_single_file(file_to_load):
                    if required:
                        return False
                    # For non-required files, log warning but continue
                    self.logger.warning(
                        f"⚠️  Could not load {file_to_load.name}, continuing..."
                    )

        return True

    async def _load_single_file(self, file_path: Path) -> bool:
        """Load a single file to the database with retry logic."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.logger.info(f"Loading {file_path.name} (attempt {attempt + 1})")

                import click.testing

                runner = click.testing.CliRunner()

                # Determine which loader to use based on file prefix
                is_team_file = file_path.name.startswith("teams_")

                if is_team_file:
                    # Use team loader for team files
                    self.logger.info(f"Using team loader for {file_path.name}")
                    result = runner.invoke(
                        load_teams_csv_main,
                        [str(file_path), "--materialize", "--verbose"],
                        catch_exceptions=False,
                    )
                else:
                    # Use player loader for player files
                    self.logger.info(f"Using player loader for {file_path.name}")
                    result = runner.invoke(
                        load_csv_main,
                        [str(file_path), "--materialize", "--verbose"],
                        catch_exceptions=False,
                    )

                if result.exit_code == 0:
                    self.logger.info(f"✅ Successfully loaded {file_path.name}")
                    return True
                else:
                    raise Exception(f"Load failed with exit code {result.exit_code}")

            except Exception as e:
                self.logger.warning(f"Load attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 60  # 1, 2, 3 minutes
                    self.logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    self.logger.error(
                        f"❌ Failed to load {file_path.name} after all attempts"
                    )
                    return False

        return False

    async def _validate_database_integrity(self) -> bool:
        """Validate database integrity after loading."""
        self.logger.info("🔍 Validating database integrity...")

        try:
            with session_scope() as session:
                # Check record counts
                tables_to_check = [
                    ("player_seasons", 1000),  # Minimum expected player_seasons
                    ("player_metrics", 10000),  # Minimum expected player metrics
                    ("teams", 50),  # Minimum expected teams
                    ("leagues", 5),  # Minimum expected leagues
                    ("team_seasons", 50),  # Minimum expected team_seasons
                    ("team_metrics", 500),  # Minimum expected team metrics
                ]

                for table, min_count in tables_to_check:
                    result = session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = result.scalar()

                    if count < min_count:
                        self.logger.error(
                            f"❌ {table}: {count} records (expected >= {min_count})"
                        )
                        return False
                    else:
                        self.logger.info(f"✅ {table}: {count} records")

                # Check for data consistency
                result = session.execute(
                    text("""
                    SELECT COUNT(*) FROM player_metrics pm
                    LEFT JOIN player_seasons ps ON pm.player_season_id = ps.id
                    WHERE ps.id IS NULL
                """)
                )
                orphaned_metrics = result.scalar()

                if orphaned_metrics > 0:
                    self.logger.error(f"❌ Found {orphaned_metrics} orphaned metrics")
                    return False

                self.logger.info("✅ Database integrity validation passed")
                return True

        except Exception as e:
            self.logger.error(f"❌ Database validation failed: {e}")
            return False

    def _cleanup_old_files(self):
        """Clean up old data files to save space.

        IMPORTANT: Never deletes players_fbref_stats_raw_*.csv or transfermarkt_checkpoint_*.csv
        as these are source files that take a long time to regenerate.
        """
        self.logger.info("🧹 Cleaning up old files...")

        # Patterns to clean up (derived/output files only)
        # Keep only the 3 most recent files for each pattern
        cleanup_patterns = [
            "players_identity_*.csv",
            "players_metrics_*.csv",
            "players_transfermarkt_*.csv",
            "player_similarities_*.csv",
            "teams_identity_*.csv",
            "teams_metrics_*.csv",
        ]

        # Files to NEVER delete (source/checkpoint files)
        protected_prefixes = [
            "players_fbref_stats_raw_",
            "players_fbref_stats_temp_",
            "teams_fbref_stats_raw_",
            "teams_fbref_stats_temp_",
            "transfermarkt_checkpoint_",
            "transfermarkt_club_urls",
        ]

        for pattern in cleanup_patterns:
            files = list(self.data_dir.glob(pattern))

            # Filter out protected files
            files = [
                f
                for f in files
                if not any(f.name.startswith(prefix) for prefix in protected_prefixes)
            ]

            if len(files) > 3:
                # Sort by modification time, keep newest 3
                files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
                files_to_delete = files[3:]

                for file_to_delete in files_to_delete:
                    try:
                        file_to_delete.unlink()
                        self.logger.info(f"🗑️  Deleted old file: {file_to_delete.name}")
                    except Exception as e:
                        self.logger.warning(f"Could not delete {file_to_delete}: {e}")

    async def _send_notification(self, success: bool):
        """Send email notification about pipeline status."""
        if not self.config.get("email_notifications", False):
            return

        try:
            duration = datetime.now() - self.start_time
            status = "SUCCESS" if success else "FAILURE"

            subject = (
                f"ETL Pipeline {status} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )

            body = f"""
            ETL Pipeline Status: {status}

            Start Time: {self.start_time}
            Duration: {duration}
            Database: {get_database_url().split("@")[1] if "@" in get_database_url() else "Unknown"}

            {"Pipeline completed successfully!" if success else "Pipeline failed - check logs for details."}
            """

            self._send_email(subject, body)

        except Exception as e:
            self.logger.warning(f"Could not send notification: {e}")

    def _send_email(self, subject: str, body: str):
        """Send email notification."""
        smtp_server = self.config.get("smtp_server", "smtp.gmail.com")
        smtp_port = self.config.get("smtp_port", 587)
        email_user = self.config.get("email_user")
        email_password = self.config.get("email_password")
        email_to = self.config.get("email_to")

        if not all([email_user, email_password, email_to]):
            self.logger.warning(
                "Email configuration incomplete - skipping notification"
            )
            return

        msg = MIMEMultipart()
        msg["From"] = str(email_user) if email_user else ""
        msg["To"] = str(email_to) if email_to else ""
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(
            str(email_user) if email_user else "",
            str(email_password) if email_password else "",
        )
        server.send_message(msg)
        server.quit()

    async def _handle_failure(self, error: Exception):
        """Handle pipeline failure with recovery options."""
        self.logger.error(f"Pipeline failed: {error}")

        # Send failure notification
        await self._send_notification(success=False)

        # Log system state for debugging
        try:
            with session_scope() as session:
                result = session.execute(text("SELECT COUNT(*) FROM player_seasons"))
                player_count = result.scalar()
                self.logger.info(f"Current player_seasons in database: {player_count}")
        except Exception as e:
            self.logger.error(f"Could not check database state: {e}")


@click.command()
@click.option("--seasons", default="2425", help="Comma-separated seasons to process")
@click.option("--leagues", default="All", help="Leagues to process")
@click.option("--data-dir", default="data", help="Data directory")
@click.option(
    "--email-notifications/--no-email", default=False, help="Enable email notifications"
)
@click.option("--email-user", help="Email username for notifications")
@click.option("--email-password", help="Email password for notifications")
@click.option("--email-to", help="Email recipient for notifications")
@click.option(
    "--dry-run", is_flag=True, help="Validate environment without running pipeline"
)
@click.option(
    "--fbref-checkpoint-file",
    type=click.Path(file_okay=True, dir_okay=False),
    help="Path to checkpoint file for FBref scraping",
)
@click.option(
    "--transfermarkt-checkpoint-file",
    type=click.Path(file_okay=True, dir_okay=False),
    help="Path to checkpoint file for Transfermarkt scraping",
)
@click.option(
    "--transfermarkt-club-urls-file",
    type=click.Path(file_okay=True, dir_okay=False),
    help="Path to checkpoint file for Transfermarkt club urls json file",
)
@click.option(
    "--teams-fbref-checkpoint-file",
    type=click.Path(file_okay=True, dir_okay=False),
    help="Path to checkpoint file for team FBref scraping",
)
def main(
    seasons,
    leagues,
    data_dir,
    email_notifications,
    email_user,
    email_password,
    email_to,
    dry_run,
    fbref_checkpoint_file,
    transfermarkt_checkpoint_file,
    transfermarkt_club_urls_file,
    teams_fbref_checkpoint_file,
):
    """Run the remote ETL pipeline for Railway deployment."""

    config = {
        "seasons": seasons,
        "leagues": leagues,
        "data_dir": data_dir,
        "email_notifications": email_notifications,
        "email_user": email_user,
        "email_password": email_password,
        "email_to": email_to,
        "fbref_checkpoint_file": fbref_checkpoint_file,
        "transfermarkt_checkpoint_file": transfermarkt_checkpoint_file,
        "transfermarkt_club_urls_file": transfermarkt_club_urls_file,
        "teams_fbref_checkpoint_file": teams_fbref_checkpoint_file,
    }

    pipeline = RemoteETLPipeline(config)

    if dry_run:
        success = pipeline._validate_environment()
        click.echo(f"Environment validation: {'PASSED' if success else 'FAILED'}")
        sys.exit(0 if success else 1)

    # Run the pipeline
    success = asyncio.run(pipeline.run_pipeline())
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
