#!/usr/bin/env python3
"""View and analyze solar forecast performance data."""

import os
import sys
import csv
from datetime import datetime, timedelta
from typing import List, Dict

# Add to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from modules.data_logger import DataLogger
from src.config import ConfigManager


def print_header(title: str):
    """Print a formatted header."""
    print(f"\n{'='*70}")
    print(f"{title:^70}")
    print(f"{'='*70}\n")


def print_table(headers: List[str], rows: List[List[str]], col_widths: List[int] = None):
    """Print a formatted table."""
    if not col_widths:
        col_widths = [max(len(str(row[i])) for row in [headers] + rows) + 2 
                      for i in range(len(headers))]
    
    # Print header
    header_row = "".join(f"{h:<{col_widths[i]}}" for i, h in enumerate(headers))
    print(header_row)
    print("-" * sum(col_widths))
    
    # Print rows
    for row in rows:
        print("".join(f"{str(cell):<{col_widths[i]}}" for i, cell in enumerate(row)))


def view_predictions(logger: DataLogger, days: int = None):
    """View recent predictions."""
    print_header("Recent Predictions")
    
    if not os.path.isfile(logger.predictions_file):
        print("No predictions logged yet.")
        return
    
    with open(logger.predictions_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    if not rows:
        print("No predictions logged yet.")
        return
    
    # Filter to recent days if specified
    if days:
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        rows = [r for r in rows if r["Prediction Date"] >= cutoff]
    
    # Display key columns
    headers = ["Date", "Forecast", "Coverage", "Current", "Target", "Rate"]
    table_rows = []
    
    for row in rows[-10:]:  # Last 10 entries
        table_rows.append([
            row["Prediction Date"],
            f"{row['Forecast (kWh)']} kWh",
            f"{row['Solar Coverage (%)']}%",
            f"{row['Current SOC (%)']}%",
            f"{row['Target SOC (%)']}%",
            f"{row['Charge Rate Set (%)']}%"
        ])
    
    print_table(headers, table_rows)
    print(f"\nTotal predictions: {len(rows)}")


def view_actuals(logger: DataLogger, days: int = None):
    """View recent actual results."""
    print_header("Recent Actual Results")
    
    if not os.path.isfile(logger.actuals_file):
        print("No actuals logged yet.")
        return
    
    with open(logger.actuals_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    if not rows:
        print("No actuals logged yet.")
        return
    
    # Filter to recent days if specified
    if days:
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        rows = [r for r in rows if r["Date"] >= cutoff]
    
    # Display key columns
    headers = ["Date", "Generation", "SOC Evening", "Charge Energy"]
    table_rows = []
    
    for row in rows[-10:]:  # Last 10 entries
        table_rows.append([
            row["Date"],
            f"{row['Actual Generation (kWh)']} kWh",
            f"{row['SOC at Evening (%)']}%" if row.get('SOC at Evening (%)') else "N/A",
            f"{row['Charge Energy (kWh)']} kWh" if row.get('Charge Energy (kWh)') else "N/A"
        ])
    
    print_table(headers, table_rows)
    print(f"\nTotal actuals: {len(rows)}")


def view_summary(logger: DataLogger, days: int = None):
    """View performance summary."""
    print_header("Performance Summary")
    
    # Generate fresh summary
    logger.generate_performance_summary()
    
    if not os.path.isfile(logger.summary_file):
        print("No summary data available yet.")
        return
    
    with open(logger.summary_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    if not rows:
        print("No summary data available yet.")
        return
    
    # Filter to recent days if specified
    if days:
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        rows = [r for r in rows if r["Date"] >= cutoff]
    
    # Display all columns
    headers = ["Date", "Forecast", "Actual", "Accuracy", "Error", "Target", "Charge Eff", "Performance"]
    table_rows = []
    
    total_accuracy = 0
    count = 0
    
    for row in rows:
        if row["Accuracy (%)"] != "N/A":
            accuracy_val = float(row["Accuracy (%)"])
            total_accuracy += accuracy_val
            count += 1
            
            # Color code accuracy (just show indicator)
            if accuracy_val >= 95:
                perf_indicator = "***"
            elif accuracy_val >= 85:
                perf_indicator = "** "
            elif accuracy_val >= 75:
                perf_indicator = "*  "
            else:
                perf_indicator = "!  "
        else:
            perf_indicator = "..."
        
        charge_eff = row.get("Charge Efficiency (%)", "")
        
        table_rows.append([
            row["Date"],
            f"{row['Forecast (kWh)']} kWh",
            f"{row['Actual (kWh)']} kWh" if row["Actual (kWh)"] != "N/A" else "Pending",
            f"{row['Accuracy (%)']}%" if row["Accuracy (%)"] != "N/A" else "N/A",
            f"{row['Error (kWh)']} kWh" if row["Error (kWh)"] != "N/A" else "N/A",
            f"{row['Target SOC (%)']}%",
            f"{charge_eff}%" if charge_eff else "N/A",
            f"{perf_indicator} {row['Performance']}"
        ])
    
    print_table(headers, table_rows)
    
    if count > 0:
        avg_accuracy = total_accuracy / count
        print(f"\n{'─'*70}")
        print(f"Average Accuracy: {avg_accuracy:.1f}%")
        print(f"Days Analyzed: {count}")
        
        if avg_accuracy >= 90:
            print("Status: *** Excellent")
        elif avg_accuracy >= 80:
            print("Status: **  Good")
        elif avg_accuracy >= 70:
            print("Status: *   Fair - Consider tuning")
        else:
            print("Status: !   Poor - Review configuration")
    else:
        print("\nInsufficient data for accuracy calculation.")


def view_insights(logger: DataLogger, config: ConfigManager = None):
    """Generate insights from the data."""
    print_header("Insights & Recommendations")
    
    # Load config if not provided
    if config is None:
        config_path = 'conf/growatt-charger.ini'
        if not os.path.exists(config_path):
            config_path = '/opt/growatt-charger/conf/growatt-charger.ini'
        try:
            config = ConfigManager(config_path)
            confidence_pct = int(config.forecast.confidence * 100)
        except:
            confidence_pct = 80  # Fallback if config can't be loaded
    else:
        confidence_pct = int(config.forecast.confidence * 100)
    
    if not os.path.isfile(logger.summary_file):
        print("No data available for insights yet.")
        return
    
    logger.generate_performance_summary()
    
    with open(logger.summary_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = [r for r in reader if r["Accuracy (%)"] != "N/A"]
    
    if len(rows) < 3:
        print("Need at least 3 days of data for meaningful insights.")
        print(f"Current data points: {len(rows)}")
        return
    
    # Calculate statistics
    accuracies = [float(r["Accuracy (%)"]) for r in rows]
    errors = [float(r["Error (kWh)"]) for r in rows]
    
    avg_accuracy = sum(accuracies) / len(accuracies)
    avg_error = sum(errors) / len(errors)
    
    over_predictions = sum(1 for e in errors if e < 0)
    under_predictions = sum(1 for e in errors if e > 0)
    
    print(f"Data Points: {len(rows)} days\n")
    
    print("📊 Forecast Accuracy")
    print(f"   Average: {avg_accuracy:.1f}%")
    print(f"   Best: {max(accuracies):.1f}%")
    print(f"   Worst: {min(accuracies):.1f}%")
    
    print(f"\n📈 Forecast Bias")
    print(f"   Average Error: {avg_error:+.2f} kWh")
    print(f"   Over-predictions: {over_predictions} days")
    print(f"   Under-predictions: {under_predictions} days")
    
    # Determine bias
    if abs(avg_error) < 0.5:
        bias_msg = "✓ Well calibrated"
    elif avg_error > 0:
        bias_msg = "↑ Tends to under-predict (forecasts too low)"
    else:
        bias_msg = "↓ Tends to over-predict (forecasts too high)"
    print(f"   Bias: {bias_msg}")
    
    print(f"\n💡 Recommendations")
    
    # Recommendation 1: Confidence factor
    if avg_error > 1.0:
        print(f"   • Consider INCREASING confidence factor (currently using {confidence_pct}%)")
        print("     Forecasts are consistently too low")
        new_conf = min(100, confidence_pct + 10)
        print(f"     Try: confidence = {new_conf/100:.1f} in config")
    elif avg_error < -1.0:
        print(f"   • Consider DECREASING confidence factor (currently using {confidence_pct}%)")
        print("     Forecasts are consistently too high")
        new_conf = max(50, confidence_pct - 10)
        print(f"     Try: confidence = {new_conf/100:.1f} in config")
    else:
        print(f"   • Confidence factor ({confidence_pct}%) appears well-calibrated")
    
    # Recommendation 2: SOC thresholds
    if avg_accuracy >= 90:
        print("   • Forecast accuracy is excellent!")
        print("   • Consider being more aggressive with SOC targets")
        print("     (charge less on high-forecast days)")
    elif avg_accuracy < 75:
        print("   • Forecast accuracy needs improvement")
        print("   • Consider being more conservative with SOC targets")
        print("     (charge more to be safe)")
    
    # Recommendation 3: Seasonal adjustment
    current_month = datetime.now().month
    if current_month in [11, 12, 1, 2]:  # Winter
        print("   • Winter months: Consider increasing minimum charge %")
    elif current_month in [5, 6, 7, 8]:  # Summer
        print("   • Summer months: Can reduce minimum charge % if desired")


def main():
    """Main entry point."""
    logger = DataLogger()
    
    # Load config for insights
    config = None
    config_path = 'conf/growatt-charger.ini'
    if not os.path.exists(config_path):
        config_path = '/opt/growatt-charger/conf/growatt-charger.ini'
    
    try:
        config = ConfigManager(config_path)
    except Exception as e:
        print(f"Note: Could not load config ({e}), using defaults for insights")
    
    print_header("Growatt Solar Forecast Performance Analyzer")
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        days = int(sys.argv[2]) if len(sys.argv) > 2 else None
        
        if command == "predictions":
            view_predictions(logger, days)
        elif command == "actuals":
            view_actuals(logger, days)
        elif command == "summary":
            view_summary(logger, days)
        elif command == "insights":
            view_insights(logger, config)
        else:
            print(f"Unknown command: {command}")
            print_usage()
    else:
        # Default: show everything
        view_predictions(logger, 7)
        view_actuals(logger, 7)
        view_summary(logger, 7)
        view_insights(logger, config)


def print_usage():
    """Print usage information."""
    print("\nUsage:")
    print("  python view_performance.py [command] [days]")
    print("\nCommands:")
    print("  predictions [days]  - Show recent predictions")
    print("  actuals [days]      - Show actual generation results")
    print("  summary [days]      - Show performance summary")
    print("  insights            - Show insights and recommendations")
    print("  (no command)        - Show all (last 7 days)")
    print("\nExamples:")
    print("  python view_performance.py")
    print("  python view_performance.py summary 14")
    print("  python view_performance.py insights")


if __name__ == "__main__":
    main()