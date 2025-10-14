"""Enhanced data logging for forecast accuracy tracking and optimization."""

import os
import csv
from datetime import datetime, timedelta
from typing import Dict, Any, Optional


class DataLogger:
    """Handles CSV logging of predictions, actuals, and performance metrics."""
    
    def __init__(self, output_dir: str = "output"):
        """
        Initialize the data logger.
        
        Args:
            output_dir: Directory to store CSV files
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        self.predictions_file = os.path.join(output_dir, "predictions.csv")
        self.actuals_file = os.path.join(output_dir, "actuals.csv")
        self.summary_file = os.path.join(output_dir, "performance_summary.csv")
    
    def log_prediction(
        self,
        prediction_date: str,
        forecast_wh: float,
        solar_coverage_pct: float,
        current_soc: float,
        target_soc: int,
        charge_rate_pct: int,
        off_peak_start: str,
        off_peak_end: str,
        battery_capacity_wh: int,
        average_load_w: float,
        expected_soc_increase: float = None
    ) -> None:
        """
        Log the prediction made at 22:00 for the next day.
        
        Args:
            prediction_date: Date being predicted for (YYYY-MM-DD)
            forecast_wh: Forecasted generation in Wh
            solar_coverage_pct: Percentage of daily needs covered by forecast
            current_soc: Current battery SOC when prediction made
            target_soc: Target SOC set for charging
            charge_rate_pct: Charge rate percentage set
            off_peak_start: Off-peak start time
            off_peak_end: Off-peak end time
            battery_capacity_wh: Battery capacity in Wh
            average_load_w: Average load in watts
            expected_soc_increase: Expected SOC increase from charging
        """
        file_exists = os.path.isfile(self.predictions_file)
        
        with open(self.predictions_file, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            
            if not file_exists:
                writer.writerow([
                    "Prediction Date",
                    "Logged At",
                    "Forecast (Wh)",
                    "Forecast (kWh)",
                    "Solar Coverage (%)",
                    "Current SOC (%)",
                    "Target SOC (%)",
                    "Expected SOC Increase (%)",
                    "Charge Rate Set (%)",
                    "Off-Peak Window",
                    "Battery Capacity (Wh)",
                    "Avg Load (W)",
                    "Daily Consumption (Wh)"
                ])
            
            logged_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            soc_increase = expected_soc_increase if expected_soc_increase else (target_soc - current_soc)
            daily_consumption = average_load_w * 24
            
            writer.writerow([
                prediction_date,
                logged_at,
                int(forecast_wh),
                round(forecast_wh / 1000, 2),
                round(solar_coverage_pct, 1),
                round(current_soc, 1),
                target_soc,
                round(soc_increase, 1),
                charge_rate_pct,
                f"{off_peak_start}-{off_peak_end}",
                battery_capacity_wh,
                average_load_w,
                int(daily_consumption)
            ])
    
    def log_actual(
        self,
        actual_date: str,
        actual_generation_wh: float,
        soc_at_sunset: Optional[float] = None,
        soc_at_morning: Optional[float] = None,
        charge_energy_wh: Optional[float] = None,
        actual_soc_increase: Optional[float] = None,
        notes: str = ""
    ) -> None:
        """
        Log the actual results for a given day.
        
        Args:
            actual_date: Date of actual results (YYYY-MM-DD)
            actual_generation_wh: Actual generation in Wh
            soc_at_sunset: Battery SOC at sunset (if available)
            soc_at_morning: Battery SOC at morning (if available)
            charge_energy_wh: Actual energy charged overnight in Wh
            actual_soc_increase: Actual SOC increase from charging
            notes: Any additional notes
        """
        file_exists = os.path.isfile(self.actuals_file)
        
        with open(self.actuals_file, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            
            if not file_exists:
                writer.writerow([
                    "Date",
                    "Logged At",
                    "Actual Generation (Wh)",
                    "Actual Generation (kWh)",
                    "SOC at Evening (%)",
                    "SOC at Morning (%)",
                    "Actual SOC Increase (%)",
                    "Charge Energy (Wh)",
                    "Charge Energy (kWh)",
                    "Notes"
                ])
            
            logged_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            soc_change = actual_soc_increase
            if soc_change is None and soc_at_sunset is not None and soc_at_morning is not None:
                soc_change = round(soc_at_sunset - soc_at_morning, 1)
            
            writer.writerow([
                actual_date,
                logged_at,
                int(actual_generation_wh),
                round(actual_generation_wh / 1000, 2),
                round(soc_at_sunset, 1) if soc_at_sunset else "",
                round(soc_at_morning, 1) if soc_at_morning else "",
                round(soc_change, 1) if soc_change else "",
                int(charge_energy_wh) if charge_energy_wh else "",
                round(charge_energy_wh / 1000, 2) if charge_energy_wh else "",
                notes
            ])
    
    def generate_performance_summary(self) -> None:
        """
        Generate a performance summary by matching predictions with actuals.
        Creates a combined CSV showing forecast accuracy and performance.
        """
        # Read predictions
        predictions = {}
        if os.path.isfile(self.predictions_file):
            with open(self.predictions_file, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    date = row["Prediction Date"]
                    predictions[date] = row
        
        # Read actuals
        actuals = {}
        if os.path.isfile(self.actuals_file):
            with open(self.actuals_file, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    date = row["Date"]
                    actuals[date] = row
        
        # Combine and calculate metrics
        with open(self.summary_file, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            
            writer.writerow([
                "Date",
                "Forecast (kWh)",
                "Actual (kWh)",
                "Accuracy (%)",
                "Error (kWh)",
                "Solar Coverage Predicted (%)",
                "Target SOC (%)",
                "Expected SOC Increase (%)",
                "Actual SOC Increase (%)",
                "Charge Rate Set (%)",
                "Charge Energy (kWh)",
                "Charge Efficiency (%)",
                "SOC at Evening (%)",
                "Performance"
            ])
            
            for date in sorted(predictions.keys()):
                pred = predictions[date]
                actual = actuals.get(date)
                
                if actual:
                    forecast_kwh = float(pred["Forecast (kWh)"])
                    actual_kwh = float(actual["Actual Generation (kWh)"])
                    
                    accuracy = (actual_kwh / forecast_kwh * 100) if forecast_kwh > 0 else 0
                    error = actual_kwh - forecast_kwh
                    
                    # Calculate charge efficiency
                    expected_soc_increase = float(pred.get("Expected SOC Increase (%)", 0))
                    actual_soc_increase = float(actual.get("Actual SOC Increase (%)", 0)) if actual.get("Actual SOC Increase (%)") else None
                    charge_efficiency = None
                    if expected_soc_increase > 0 and actual_soc_increase:
                        charge_efficiency = (actual_soc_increase / expected_soc_increase * 100)
                    
                    # Determine performance rating
                    if accuracy >= 95:
                        performance = "Excellent"
                    elif accuracy >= 85:
                        performance = "Good"
                    elif accuracy >= 75:
                        performance = "Fair"
                    else:
                        performance = "Poor"
                    
                    # Handle both old and new column names
                    charge_rate_key = "Charge Rate Set (%)" if "Charge Rate Set (%)" in pred else "Charge Rate (%)"
                    
                    writer.writerow([
                        date,
                        pred["Forecast (kWh)"],
                        actual["Actual Generation (kWh)"],
                        round(accuracy, 1),
                        round(error, 2),
                        pred["Solar Coverage (%)"],
                        pred["Target SOC (%)"],
                        pred.get("Expected SOC Increase (%)", ""),
                        actual.get("Actual SOC Increase (%)", ""),
                        pred[charge_rate_key],
                        actual.get("Charge Energy (kWh)", ""),
                        round(charge_efficiency, 1) if charge_efficiency else "",
                        actual.get("SOC at Evening (%)", ""),
                        performance
                    ])
                else:
                    # Prediction exists but no actual data yet
                    charge_rate_key = "Charge Rate Set (%)" if "Charge Rate Set (%)" in pred else "Charge Rate (%)"
                    
                    writer.writerow([
                        date,
                        pred["Forecast (kWh)"],
                        "N/A",
                        "N/A",
                        "N/A",
                        pred["Solar Coverage (%)"],
                        pred["Target SOC (%)"],
                        pred.get("Expected SOC Increase (%)", ""),
                        "N/A",
                        pred[charge_rate_key],
                        "N/A",
                        "N/A",
                        "N/A",
                        "Pending"
                    ])
    
    def get_recent_accuracy(self, days: int = 7) -> Optional[float]:
        """
        Calculate average forecast accuracy for recent days.
        
        Args:
            days: Number of recent days to analyze
            
        Returns:
            Average accuracy percentage, or None if insufficient data
        """
        if not os.path.isfile(self.summary_file):
            return None
        
        accuracies = []
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        with open(self.summary_file, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["Date"] >= cutoff_date and row["Accuracy (%)"] != "N/A":
                    try:
                        accuracy = float(row["Accuracy (%)"])
                        accuracies.append(accuracy)
                    except (ValueError, KeyError):
                        continue
        
        if accuracies:
            return sum(accuracies) / len(accuracies)
        return None
    
    def print_recent_summary(self, days: int = 7) -> None:
        """
        Print a summary of recent performance.
        
        Args:
            days: Number of days to include in summary
        """
        avg_accuracy = self.get_recent_accuracy(days)
        
        print(f"\n{'='*60}")
        print(f"Performance Summary (Last {days} Days)")
        print(f"{'='*60}")
        
        if avg_accuracy:
            print(f"Average Forecast Accuracy: {avg_accuracy:.1f}%")
            
            if avg_accuracy >= 90:
                print("Status: Excellent - Forecasts are highly accurate")
            elif avg_accuracy >= 80:
                print("Status: Good - Forecasts are reliable")
            elif avg_accuracy >= 70:
                print("Status: Fair - Consider adjusting confidence factor")
            else:
                print("Status: Poor - Review configuration and thresholds")
        else:
            print("Insufficient data - need at least one complete day")
        
        print(f"{'='*60}\n")