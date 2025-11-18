#!/usr/bin/env python
"""Review peak-window boost decisions and effectiveness."""

import csv
import os
import sys
from collections import defaultdict
from typing import Dict, List

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class PeakDecisionAnalyzer:
    """Analyzes peak-window boost decisions and their effectiveness."""

    def __init__(self, output_dir: str = "output"):
        """Initialize analyzer."""
        self.output_dir = output_dir
        self.peak_decisions_file = os.path.join(output_dir, "peak_decisions.csv")
        self.predictions_file = os.path.join(output_dir, "predictions.csv")
        self.actuals_file = os.path.join(output_dir, "actuals.csv")

    def analyze(self) -> None:
        """Run comprehensive analysis of peak decisions."""
        if not os.path.isfile(self.peak_decisions_file):
            print("No peak decisions found yet. Run afternoon_peak_check.py to generate data.")
            return

        peak_decisions = self._load_peak_decisions()
        predictions = self._load_predictions()
        actuals = self._load_actuals()

        print("\n" + "=" * 70)
        print("PEAK-WINDOW BOOST DECISION ANALYSIS (14:00 Check)")
        print("=" * 70)

        # Summary statistics
        self._print_summary_stats(peak_decisions)

        # Forecast accuracy for peak decisions
        self._print_forecast_accuracy(peak_decisions, predictions)

        # Boost effectiveness (did boosting prevent undersupply?)
        self._print_boost_effectiveness(peak_decisions, actuals)

        # Recommendations for tuning
        self._print_recommendations(peak_decisions, predictions, actuals)

        # Export detailed report
        self._export_detailed_report(peak_decisions, predictions, actuals)

        print("\n" + "=" * 70)

    def _load_peak_decisions(self) -> List[Dict]:
        """Load peak decisions from CSV."""
        decisions = []
        if not os.path.isfile(self.peak_decisions_file):
            return decisions

        with open(self.peak_decisions_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            decisions = list(reader)

        return decisions

    def _load_predictions(self) -> Dict[str, float]:
        """Load forecasted values by date."""
        predictions = {}
        if not os.path.isfile(self.predictions_file):
            return predictions

        with open(self.predictions_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    date_str = row.get("Date", "").strip()
                    forecast_wh = float(row.get("Forecast_Wh", 0))
                    predictions[date_str] = forecast_wh
                except (ValueError, KeyError):
                    pass

        return predictions

    def _load_actuals(self) -> Dict[str, float]:
        """Load actual generation by date."""
        actuals = {}
        if not os.path.isfile(self.actuals_file):
            return actuals

        with open(self.actuals_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    date_str = row.get("Date", "").strip()
                    actual_wh = float(row.get("Actual_Wh", 0))
                    actuals[date_str] = actual_wh
                except (ValueError, KeyError):
                    pass

        return actuals

    def _print_summary_stats(self, decisions: List[Dict]) -> None:
        """Print summary statistics."""
        if not decisions:
            print("\nNo peak decisions to analyze.")
            return

        total = len(decisions)
        boosted = sum(1 for d in decisions if d.get("Decision") == "BOOST")
        not_boosted = total - boosted

        avg_soc = sum(float(d.get("Current SOC (%)", 0)) for d in decisions) / total
        avg_forecast = sum(float(d.get("Remaining Forecast (kWh)", 0)) for d in decisions) / total

        print(f"\nDecisions Analyzed: {total}")
        print(f"  Boosts Recommended: {boosted} ({100*boosted/total:.1f}%)")
        print(f"  No Boost Needed: {not_boosted} ({100*not_boosted/total:.1f}%)")
        print("\nAverage Conditions at 14:00:")
        print(f"  Battery SOC: {avg_soc:.1f}%")
        print(f"  Remaining Forecast: {avg_forecast:.2f} kWh")

    def _print_forecast_accuracy(
        self, decisions: List[Dict], predictions: Dict[str, float]
    ) -> None:
        """Compare predicted vs actual for dates with peak decisions."""
        if not predictions:
            print("\nNo prediction data available for accuracy analysis.")
            return

        matches = []
        for decision in decisions:
            date_str = decision.get("Date", "").strip()
            if date_str in predictions:
                predicted_kwh = predictions[date_str] / 1000
                reported_kwh = float(decision.get("Remaining Forecast (kWh)", 0))
                matches.append(
                    {"date": date_str, "predicted": predicted_kwh, "reported": reported_kwh}
                )

        if not matches:
            return

        print(f"\nForecast Accuracy for Peak Decisions ({len(matches)} days):")

        errors = []
        for match in matches:
            error_pct = abs(match["predicted"] - match["reported"]) / max(match["predicted"], 0.1)
            errors.append(error_pct)

        avg_error = sum(errors) / len(errors)
        max_error = max(errors)
        min_error = min(errors)

        print(f"  Average Error: {100*avg_error:.1f}%")
        print(f"  Min Error: {100*min_error:.1f}%")
        print(f"  Max Error: {100*max_error:.1f}%")

    def _print_boost_effectiveness(self, decisions: List[Dict], actuals: Dict[str, float]) -> None:
        """Analyze if boosts were effective in preventing undersupply."""
        if not actuals:
            print("\nNo actual generation data available for effectiveness analysis.")
            return

        boosted_shortfalls = []
        not_boosted_shortfalls = []

        for decision in decisions:
            date_str = decision.get("Date", "").strip()
            decision_type = decision.get("Decision", "").strip()
            shortfall_pct = float(decision.get("Peak Shortfall (%)", 0))

            if date_str in actuals:
                # actual_wh = actuals[date_str]
                # required_kwh = float(decision.get("Peak Consumption (Wh)", 0)) / 1000

                if decision_type == "BOOST":
                    boosted_shortfalls.append(shortfall_pct)
                else:
                    not_boosted_shortfalls.append(shortfall_pct)

        print("\nBoost Effectiveness:")

        if boosted_shortfalls:
            avg_boosted = sum(boosted_shortfalls) / len(boosted_shortfalls)
            print(f"  Boosted Decisions: Avg Peak Shortfall {avg_boosted:.1f}%")

        if not_boosted_shortfalls:
            avg_not_boosted = sum(not_boosted_shortfalls) / len(not_boosted_shortfalls)
            print(f"  Not Boosted: Avg Peak Shortfall {avg_not_boosted:.1f}%")

    def _print_recommendations(
        self, decisions: List[Dict], predictions: Dict[str, float], actuals: Dict[str, float]
    ) -> None:
        """Print recommendations for tuning boost thresholds."""
        if not decisions:
            return

        print("\nRecommendations:")

        # Analyze forecast range distribution
        forecast_ranges = defaultdict(list)
        for decision in decisions:
            forecast_kwh = float(decision.get("Remaining Forecast (kWh)", 0))

            if forecast_kwh < 3:
                forecast_ranges["< 3 kWh"].append(decision.get("Decision"))
            elif forecast_kwh < 5:
                forecast_ranges["3-5 kWh"].append(decision.get("Decision"))
            elif forecast_kwh < 8:
                forecast_ranges["5-8 kWh"].append(decision.get("Decision"))
            elif forecast_kwh < 12:
                forecast_ranges["8-12 kWh"].append(decision.get("Decision"))
            else:
                forecast_ranges["12+ kWh"].append(decision.get("Decision"))

        if forecast_ranges:
            print("\n  Boost Rate by Forecast Range:")
            for range_label in sorted(forecast_ranges.keys()):
                decisions_in_range = forecast_ranges[range_label]
                boosts = sum(1 for d in decisions_in_range if d == "BOOST")
                total = len(decisions_in_range)
                boost_rate = 100 * boosts / total if total > 0 else 0
                print(f"    {range_label}: {boost_rate:.0f}% boosted ({boosts}/{total})")

        # Analyze SOC at decision time
        soc_at_boost = []
        soc_at_no_boost = []

        for decision in decisions:
            soc = float(decision.get("Current SOC (%)", 0))
            if decision.get("Decision") == "BOOST":
                soc_at_boost.append(soc)
            else:
                soc_at_no_boost.append(soc)

        if soc_at_boost and soc_at_no_boost:
            avg_boost_soc = sum(soc_at_boost) / len(soc_at_boost)
            avg_no_boost_soc = sum(soc_at_no_boost) / len(soc_at_no_boost)
            print("\n  Average SOC at Decision Time:")
            print(f"    When Boosted: {avg_boost_soc:.1f}%")
            print(f"    When Not Boosted: {avg_no_boost_soc:.1f}%")

    def _export_detailed_report(
        self, decisions: List[Dict], predictions: Dict[str, float], actuals: Dict[str, float]
    ) -> None:
        """Export detailed analysis report to CSV."""
        report_file = os.path.join(self.output_dir, "peak_decisions_analysis.csv")

        try:
            with open(report_file, "w", newline="", encoding="utf-8") as f:
                fieldnames = [
                    "Date",
                    "Decision",
                    "Current SOC",
                    "Forecast (kWh)",
                    "Peak Shortfall (%)",
                    "Required SOC (%)",
                    "Reason",
                ]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()

                for decision in decisions:
                    writer.writerow(
                        {
                            "Date": decision.get("Date", ""),
                            "Decision": decision.get("Decision", ""),
                            "Current SOC": decision.get("Current SOC (%)", ""),
                            "Forecast (kWh)": decision.get("Remaining Forecast (kWh)", ""),
                            "Peak Shortfall (%)": decision.get("Peak Shortfall (%)", ""),
                            "Required SOC (%)": decision.get("Required SOC (%)", ""),
                            "Reason": decision.get("Reason", ""),
                        }
                    )

            print(f"\nDetailed report exported to: {report_file}")
        except Exception as e:
            print(f"Failed to export detailed report: {e}")


def main():
    """Entry point."""
    output_dir = "output"

    analyzer = PeakDecisionAnalyzer(output_dir)
    analyzer.analyze()


if __name__ == "__main__":
    main()
