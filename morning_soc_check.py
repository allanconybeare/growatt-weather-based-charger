#!/usr/bin/env python3
"""
Morning SOC check script.
Runs at 05:00 to capture battery SOC immediately after overnight charging ends.
Compares actual SOC achieved vs target SOC from last night's prediction.
"""

import os
import sys
import csv
from datetime import datetime, timedelta

# Add to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.config import ConfigManager
from src.api import GrowattAPI
from src.utils import setup_logging


def get_last_night_prediction(predictions_file: str, today_date: str):
    """
    Get last night's prediction for today.
    
    Args:
        predictions_file: Path to predictions.csv
        today_date: Today's date in YYYY-MM-DD format
        
    Returns:
        Dictionary with prediction data or None
    """
    if not os.path.isfile(predictions_file):
        return None
    
    with open(predictions_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['Prediction Date'] == today_date:
                return row
    
    return None


def log_morning_soc(output_dir: str, date: str, actual_soc: float, 
                     target_soc: float, charge_rate_set: int, variance: float):
    """
    Log the morning SOC check results.
    
    Args:
        output_dir: Output directory for CSV
        date: Date in YYYY-MM-DD format
        actual_soc: Actual SOC measured at 05:00
        target_soc: Target SOC from prediction
        charge_rate_set: Charge rate that was set (%)
        variance: Difference between target and actual
    """
    morning_soc_file = os.path.join(output_dir, 'morning_soc_checks.csv')
    file_exists = os.path.isfile(morning_soc_file)
    
    with open(morning_soc_file, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        if not file_exists:
            writer.writerow([
                'Date',
                'Check Time',
                'Target SOC (%)',
                'Actual SOC (%)',
                'Variance (%)',
                'Charge Rate Set (%)',
                'Achievement (%)',
                'Status'
            ])
        
        check_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Calculate achievement percentage
        if target_soc > 0:
            achievement = (actual_soc / target_soc) * 100
        else:
            achievement = 100.0
        
        # Determine status
        if abs(variance) <= 5:
            status = 'Excellent'
        elif abs(variance) <= 10:
            status = 'Good'
        elif abs(variance) <= 15:
            status = 'Fair'
        else:
            status = 'Poor'
        
        writer.writerow([
            date,
            check_time,
            round(target_soc, 1),
            round(actual_soc, 1),
            round(variance, 1),
            charge_rate_set,
            round(achievement, 1),
            status
        ])


def main():
    """Main entry point for morning SOC check."""
    # Setup logging
    log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    logger = setup_logging(
        log_dir=log_dir,
        log_file='morning-soc-check.log',
        additional_fields={'script': 'morning-soc-check'}
    )
    
    logger.info("Starting morning SOC check...")
    
    # Load configuration
    config_path = os.getenv(
        'GROWATT_CONFIG',
        'conf/growatt-charger.ini'
    )
    
    if not os.path.exists(config_path):
        logger.error(f"Config file not found: {config_path}")
        return 1
    
    try:
        config = ConfigManager(config_path)
        
        # Initialize Growatt API
        api = GrowattAPI()
        
        # Login
        logger.info("Logging in to Growatt API...")
        growatt_config = config.growatt
        api.login(growatt_config.username, growatt_config.password)
        
        # Get device info
        if growatt_config.plant_id and growatt_config.device_sn:
            plant_id = growatt_config.plant_id
            device_sn = growatt_config.device_sn
        else:
            device_info = api.get_device_info()
            plant_id = device_info['plant_id']
            device_sn = device_info['device_sn']
        
        logger.info(f"Checking device {device_sn} at plant {plant_id}")
        
        # Get current SOC
        status = api.get_system_status(device_sn, plant_id)
        actual_soc = float(status['SOC'])
        
        logger.info(f"Current battery SOC: {actual_soc}%")
        
        # Get output directory (same level as config file, not under it)
        config_dir = os.path.dirname(os.path.abspath(config_path))
        project_root = os.path.dirname(config_dir)  # Go up one level from conf/
        output_dir = os.path.join(project_root, 'output')
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        predictions_file = os.path.join(output_dir, 'predictions.csv')
        
        today = datetime.now().strftime('%Y-%m-%d')
        prediction = get_last_night_prediction(predictions_file, today)
        
        if prediction:
            target_soc = float(prediction['Target SOC (%)'])
            
            # Handle both old and new column names
            charge_rate_key = 'Charge Rate Set (%)' if 'Charge Rate Set (%)' in prediction else 'Charge Rate (%)'
            charge_rate_set = int(prediction[charge_rate_key])
            
            variance = actual_soc - target_soc
            
            logger.info(
                f"Target SOC: {target_soc}%, "
                f"Actual SOC: {actual_soc}%, "
                f"Variance: {variance:+.1f}%"
            )
            
            # Log the morning check
            log_morning_soc(
                output_dir,
                today,
                actual_soc,
                target_soc,
                charge_rate_set,
                variance
            )
            
            # Print summary
            print(f"\n{'='*60}")
            print(f"Morning SOC Check - {today}")
            print(f"{'='*60}")
            print(f"Time: {datetime.now().strftime('%H:%M:%S')}")
            print(f"Target SOC: {target_soc}%")
            print(f"Actual SOC: {actual_soc}%")
            print(f"Variance: {variance:+.1f}%")
            print(f"Charge Rate Set: {charge_rate_set}%")
            
            if abs(variance) <= 5:
                print(f"Status: ✓ Excellent (within 5%)")
            elif abs(variance) <= 10:
                print(f"Status: ✓ Good (within 10%)")
            elif abs(variance) <= 15:
                print(f"Status: ⚠ Fair (within 15%)")
            else:
                print(f"Status: ✗ Poor (off by {abs(variance):.1f}%)")
            
            print(f"{'='*60}\n")
            
        else:
            logger.warning(f"No prediction found for {today}")
            print(f"\n{'='*60}")
            print(f"Morning SOC Check - {today}")
            print(f"{'='*60}")
            print(f"Time: {datetime.now().strftime('%H:%M:%S')}")
            print(f"Current SOC: {actual_soc}%")
            print(f"No prediction available for comparison.")
            print(f"(Predictions are made the night before at 22:00)")
            print(f"{'='*60}\n")
            
            # Still log it without a target for reference
            log_morning_soc(
                output_dir,
                today,
                actual_soc,
                0.0,  # No target
                0,    # No charge rate
                0.0   # No variance
            )
        
        logger.info("Morning SOC check completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"Morning SOC check failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())