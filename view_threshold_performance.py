"""Analyze threshold performance and suggest adjustments based on historical data."""

import csv
import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple


class ThresholdAnalyzer:
    """Analyze SOC target threshold effectiveness using prediction and actual data."""

    def __init__(
        self,
        predictions_file: str = "output/predictions.csv",
        actuals_file: str = "output/actuals.csv",
        summary_file: str = "output/performance_summary.csv",
    ):
        """
        Initialize analyzer with CSV data files.

        Args:
            predictions_file: Path to predictions.csv
            actuals_file: Path to actuals.csv
            summary_file: Path to performance_summary.csv (pre-calculated metrics)
        """
        self.predictions = self._load_csv(predictions_file)
        self.actuals = self._load_csv(actuals_file)
        self.summary = self._load_csv(summary_file)

    def _load_csv(self, filepath: str) -> List[Dict]:
        """Load CSV file and return list of dict rows."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return list(csv.DictReader(f))
        except FileNotFoundError:
            print(f"Warning: {filepath} not found", file=sys.stderr)
            return []

    def _to_float(self, value: str, default: float = 0.0) -> float:
        """Safely convert string to float, handling N/A values."""
        if value == "N/A" or value == "" or value is None:
            return default
        try:
            return float(value)
        except ValueError:
            return default

    def analyze_by_forecast_range(self, ranges: List[Tuple[float, float, str]]) -> Dict[str, Dict]:
        """
        Analyze performance grouped by forecast ranges.

        Args:
            ranges: List of (min_kwh, max_kwh, label) tuples
                   e.g., [(0, 8, "Very Poor"), (8, 15, "Poor")]

        Returns:
            Dict mapping label to metrics for that range
        """
        results = {}

        for min_kwh, max_kwh, label in ranges:
            # Find all days in this forecast range
            matching_days = [
                row
                for row in self.summary
                if min_kwh <= self._to_float(row["Forecast (kWh)"]) < max_kwh
            ]

            if not matching_days:
                continue

            # Calculate metrics for this range
            accuracy_list = [
                self._to_float(row["Accuracy (%)"])
                for row in matching_days
                if row["Accuracy (%)"] != "N/A"
            ]

            efficiency_list = [
                self._to_float(row["Charge Efficiency (%)"])
                for row in matching_days
                if row["Charge Efficiency (%)"] != "N/A"
            ]

            soc_evening_list = [
                self._to_float(row["SOC at Evening (%)"])
                for row in matching_days
                if row["SOC at Evening (%)"] != "N/A"
            ]

            exhausted_count = sum(
                1 for row in matching_days if self._to_float(row["SOC at Evening (%)"]) < 20
            )

            avg_accuracy = sum(accuracy_list) / len(accuracy_list) if accuracy_list else None
            avg_efficiency = (
                sum(efficiency_list) / len(efficiency_list) if efficiency_list else None
            )
            avg_evening_soc = (
                sum(soc_evening_list) / len(soc_evening_list) if soc_evening_list else None
            )

            results[label] = {
                "forecast_range": f"{min_kwh:.0f}–{max_kwh:.0f} kWh",
                "sample_size": len(matching_days),
                "avg_accuracy": avg_accuracy,
                "avg_efficiency": avg_efficiency,
                "avg_evening_soc": avg_evening_soc,
                "days_critically_low_soc": exhausted_count,
                "matching_days": matching_days,
            }

        return results

    def _recommend_threshold_adjustment(
        self, accuracy: Optional[float], efficiency: Optional[float], evening_soc: Optional[float]
    ) -> str:
        """Generate threshold tuning recommendation."""
        reasons = []

        if accuracy is None:
            return "Insufficient data"

        if accuracy < 65:
            reasons.append("Forecast unreliable (<65% accuracy)")

        if efficiency is not None:
            if efficiency < 80:
                reasons.append("Targets not reached (<80% efficiency) - may need higher target SOC")
            elif efficiency > 120:
                reasons.append("Consistently overcharging (>120% efficiency) - targets too high")

        if evening_soc is not None:
            if evening_soc < 15:
                reasons.append("Battery critically low at evening (<15%) - increase target SOC")
            elif evening_soc > 70:
                reasons.append("Battery underutilized (>70% at evening) - can lower target SOC")

        if not reasons:
            return "Acceptable performance - no adjustment needed"

        return "; ".join(reasons)

    def print_threshold_analysis(self, ranges: List[Tuple[float, float, str]]) -> None:
        """Print formatted threshold performance analysis."""
        results = self.analyze_by_forecast_range(ranges)

        print("\n" + "=" * 120)
        print("THRESHOLD PERFORMANCE ANALYSIS")
        print("=" * 120)

        header = (
            f"{'Forecast Range':<20} "
            f"{'Samples':<10} "
            f"{'Accuracy':<12} "
            f"{'Efficiency':<12} "
            f"{'Evening SOC':<12} "
            f"{'Critical Low':<15} "
            f"{'Recommendation':<45}"
        )
        print(header)
        print("-" * 120)

        for label, metrics in results.items():
            accuracy_str = (
                f"{metrics['avg_accuracy']:.1f}%" if metrics["avg_accuracy"] is not None else "N/A"
            )
            efficiency_str = (
                f"{metrics['avg_efficiency']:.1f}%"
                if metrics["avg_efficiency"] is not None
                else "N/A"
            )
            evening_soc_str = (
                f"{metrics['avg_evening_soc']:.1f}%"
                if metrics["avg_evening_soc"] is not None
                else "N/A"
            )

            recommendation = self._recommend_threshold_adjustment(
                metrics["avg_accuracy"], metrics["avg_efficiency"], metrics["avg_evening_soc"]
            )

            print(
                f"{label:<20} "
                f"{metrics['sample_size']:<10} "
                f"{accuracy_str:<12} "
                f"{efficiency_str:<12} "
                f"{evening_soc_str:<12} "
                f"{metrics['days_critically_low_soc']:<15} "
                f"{recommendation:<45}"
            )

        print("=" * 120 + "\n")

    def export_detailed_report(
        self, output_file: str = "output/threshold_analysis_report.csv"
    ) -> None:
        """Export detailed analysis to CSV for further review."""
        ranges = [
            (0, 8, "Very Poor"),
            (8, 15, "Poor"),
            (15, 20, "Moderate"),
            (20, 25, "Good"),
            (25, 32, "Excellent"),
        ]

        results = self.analyze_by_forecast_range(ranges)

        with open(output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "Forecast Range",
                    "Sample Size",
                    "Avg Accuracy (%)",
                    "Avg Charge Efficiency (%)",
                    "Avg Evening SOC (%)",
                    "Days Critically Low",
                    "Recommendation",
                    "Generated At",
                ]
            )

            for label, metrics in results.items():
                accuracy_str = (
                    f"{metrics['avg_accuracy']:.1f}" if metrics["avg_accuracy"] is not None else ""
                )
                efficiency_str = (
                    f"{metrics['avg_efficiency']:.1f}"
                    if metrics["avg_efficiency"] is not None
                    else ""
                )
                evening_soc_str = (
                    f"{metrics['avg_evening_soc']:.1f}"
                    if metrics["avg_evening_soc"] is not None
                    else ""
                )

                recommendation = self._recommend_threshold_adjustment(
                    metrics["avg_accuracy"], metrics["avg_efficiency"], metrics["avg_evening_soc"]
                )

                writer.writerow(
                    [
                        metrics["forecast_range"],
                        metrics["sample_size"],
                        accuracy_str,
                        efficiency_str,
                        evening_soc_str,
                        metrics["days_critically_low_soc"],
                        recommendation,
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    ]
                )

        print(f"Report exported to {output_file}")


def main():
    """Run threshold analysis."""
    import argparse

    parser = argparse.ArgumentParser(description="Analyze SOC target threshold performance")
    parser.add_argument("--export", action="store_true", help="Export detailed report to CSV")
    parser.add_argument(
        "--predictions", default="output/predictions.csv", help="Path to predictions.csv"
    )
    parser.add_argument("--actuals", default="output/actuals.csv", help="Path to actuals.csv")
    parser.add_argument(
        "--summary",
        default="output/performance_summary.csv",
        help="Path to performance_summary.csv",
    )

    args = parser.parse_args()

    analyzer = ThresholdAnalyzer(
        predictions_file=args.predictions, actuals_file=args.actuals, summary_file=args.summary
    )

    # Define forecast ranges based on summer max of 32 kWh
    ranges = [
        (0, 8, "Very Poor"),
        (8, 15, "Poor"),
        (15, 20, "Moderate"),
        (20, 25, "Good"),
        (25, 32, "Excellent"),
    ]

    analyzer.print_threshold_analysis(ranges)

    if args.export:
        analyzer.export_detailed_report()


if __name__ == "__main__":
    main()
