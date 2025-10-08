import logging
from logging.handlers import RotatingFileHandler
import os
import csv
import time
from datetime import datetime

# Get base directory relative to this file
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LOG_DIR = os.path.join(BASE_DIR, "logs")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

def setup_logger(name="growatt-charger", max_bytes=1_000_000, backup_count=5):
    # Ensure log and output directories exist
    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")

    # Console
    sh = logging.StreamHandler()
    sh.setFormatter(formatter)
    logger.addHandler(sh)

    # Rotating file
    log_path = os.path.join(LOG_DIR, f"{name}.log")
    fh = RotatingFileHandler(log_path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8")
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    return logger

def exit_printing(output_string, logger=None):
    now = datetime.now()
    dt_string = now.strftime("%Y-%m-%d %H:%M:%S")

    # Write to latest.txt
    latest_path = os.path.join(OUTPUT_DIR, "latest.txt")
    with open(latest_path, "w", encoding="utf-8") as latest_file:
        for line in output_string:
            latest_file.write(line + "\n")

    # Append to rotating log
    if logger:
        logger.info(f"--- Run at {dt_string} ---")
        for line in output_string:
            logger.info(line)

def cleanup_old_logs(log_dir=LOG_DIR, max_age_days=7):
    now = time.time()
    cutoff = now - (max_age_days * 86400)

    for fname in os.listdir(log_dir):
        fpath = os.path.join(log_dir, fname)
        if os.path.isfile(fpath) and os.path.getmtime(fpath) < cutoff:
            os.remove(fpath)

def log_run_to_csv(
    date: str,
    forecast_wh: float,
    scaled_max_soc: int,
    target_soc: float,
    current_soc: float,
    surplus_wh: float,
    grid_neutral_time: str,
    required_grid_wh: float,
    charge_rate_pct: float,
    sunset_soc: float = None,
    grid_import_wh: float = None,
    csv_path=os.path.join(OUTPUT_DIR, "summary.csv")
):
    file_exists = os.path.isfile(csv_path)
    with open(csv_path, mode="a", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow([
                "Date", "Forecast (Wh)", "Scaled Max SOC (%)", "Target SOC (%)",
                "Current SOC (%)", "Surplus PV (Wh)", "Grid-Neutral Time",
                "Required Grid Wh", "Charge Rate (%)",
                "SOC at Sunset (%)", "Grid Import (Wh)"
            ])
        writer.writerow([
            date, int(forecast_wh), scaled_max_soc, round(target_soc, 1),
            round(current_soc, 1), int(surplus_wh), grid_neutral_time,
            round(required_grid_wh, 1), round(charge_rate_pct, 1),
            round(sunset_soc, 1) if sunset_soc is not None else "",
            int(grid_import_wh) if grid_import_wh is not None else ""
        ])

