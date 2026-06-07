"""Log file maintenance — CSV retention trimming and forecast cache sweep."""

import csv
import logging
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


class LogMaintenance:
    """Trims old rows from output CSVs and sweeps stale forecast cache files."""

    # Map of CSV filename to the column that holds the record date.
    # Values in "YYYY-MM-DD HH:MM:SS" format are handled by comparing only
    # the first 10 characters so both date-only and datetime columns work.
    CSV_DATE_COLUMNS: dict = {
        "predictions.csv": "Prediction Date",
        "actuals.csv": "Date",
        "provider_comparison.csv": "Date",
        "peak_decisions.csv": "Date",
        "morning_soc_checks.csv": "Date",
        "inverter_status_checks.csv": "Check Time",
    }

    def __init__(
        self,
        output_dir: str,
        cache_dir: str,
        retention_days: int = 1095,
        cache_max_age_days: int = 7,
    ):
        """
        Args:
            output_dir: Directory containing the output CSV files.
            cache_dir: Directory containing forecast cache JSON files.
            retention_days: Number of days of CSV history to retain (default 3 years).
            cache_max_age_days: Delete cache files older than this many days (default 7).
        """
        self.output_dir = output_dir
        self.cache_dir = Path(cache_dir)
        self.retention_days = retention_days
        self.cache_max_age_days = cache_max_age_days

    def run(self) -> None:
        """Run all maintenance tasks."""
        self._trim_csv_files()
        self._sweep_cache()

    def _trim_csv_files(self) -> None:
        """Remove rows older than retention_days from all managed CSVs."""
        cutoff = (datetime.now() - timedelta(days=self.retention_days)).strftime("%Y-%m-%d")
        for filename, date_col in self.CSV_DATE_COLUMNS.items():
            path = os.path.join(self.output_dir, filename)
            if not os.path.isfile(path):
                continue
            try:
                self._trim_single_csv(path, date_col, cutoff)
            except Exception as e:
                logger.warning(f"Log maintenance: could not trim {filename}: {e}")

    def _trim_single_csv(self, path: str, date_col: str, cutoff: str) -> None:
        """Trim a single CSV, keeping rows whose date is on or after cutoff."""
        with open(path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                return
            fieldnames = list(reader.fieldnames)
            rows = list(reader)

        if not rows:
            return

        kept = []
        removed = 0
        for row in rows:
            raw = row.get(date_col, "")
            row_date = raw[:10] if raw else ""
            if row_date >= cutoff:
                kept.append(row)
            else:
                removed += 1

        if removed == 0:
            return

        # Write atomically via a temp file in the same directory
        dir_name = os.path.dirname(path)
        with tempfile.NamedTemporaryFile(
            mode="w", newline="", encoding="utf-8", delete=False, dir=dir_name
        ) as tmp:
            writer = csv.DictWriter(tmp, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(kept)
            tmp_path = tmp.name

        os.replace(tmp_path, path)
        logger.info(
            f"Log maintenance: removed {removed} rows older than {cutoff} "
            f"from {os.path.basename(path)}"
        )

    def _sweep_cache(self) -> None:
        """Delete forecast cache files older than cache_max_age_days."""
        if not self.cache_dir.exists():
            return

        cutoff_mtime = datetime.now().timestamp() - (self.cache_max_age_days * 86400)
        removed = 0
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                if cache_file.stat().st_mtime < cutoff_mtime:
                    cache_file.unlink()
                    removed += 1
            except Exception as e:
                logger.warning(
                    f"Log maintenance: could not remove cache file {cache_file.name}: {e}"
                )

        if removed:
            logger.info(
                f"Log maintenance: removed {removed} cache file(s) older than "
                f"{self.cache_max_age_days} days from {self.cache_dir}"
            )
