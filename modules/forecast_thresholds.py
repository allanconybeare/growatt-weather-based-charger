"""New forecast-based SOC target calculation (simplified, data-driven)."""

from typing import Tuple


def get_scaled_soc_target_by_forecast(
    total_forecast_wh: float, minimum_charge_pct: int = 35, maximum_charge_pct: int = 95
) -> Tuple[int, str]:
    """
    Calculate optimal SOC target directly from forecast yield.

    This approach is simpler and more intuitive than coverage-based thresholds:
    - Below 8 kWh: very poor day, charge to max
    - 8–15 kWh: poor day, charge to 75%
    - 15–20 kWh: moderate day, charge to 50%
    - 20–25 kWh: good day, charge to 40%
    - 25+ kWh: excellent day, charge to 30%

    Rationale: Based on observed real-world performance (Nov 2025 data)
    and summer maximum of 32 kWh yield.

    Args:
        total_forecast_wh: Total forecasted generation for tomorrow in Wh
        minimum_charge_pct: Minimum allowed charge percentage (safety floor)
        maximum_charge_pct: Maximum allowed charge percentage (safety ceiling)

    Returns:
        Tuple of (target_soc_pct, reason_label)
    """
    forecast_kwh = total_forecast_wh / 1000

    # Define thresholds (in kWh)
    if forecast_kwh < 8:
        target_soc = maximum_charge_pct
        reason = "Very poor forecast (<8 kWh) - charge to max"
    elif forecast_kwh < 15:
        target_soc = 75
        reason = "Poor forecast (8-15 kWh) - conservative charge"
    elif forecast_kwh < 20:
        target_soc = 50
        reason = "Moderate forecast (15-20 kWh) - balanced charge"
    elif forecast_kwh < 25:
        target_soc = 40
        reason = "Good forecast (20-25 kWh) - low charge needed"
    else:
        target_soc = 30
        reason = "Excellent forecast (25+ kWh) - minimal charge"

    # Constrain to config limits (safety bounds)
    target_soc = max(minimum_charge_pct, min(maximum_charge_pct, target_soc))

    return int(target_soc), reason


if __name__ == "__main__":
    # Quick test
    test_cases = [
        (3000, "Very poor (3 kWh)"),
        (8000, "Poor (8 kWh)"),
        (15000, "Moderate (15 kWh)"),
        (20000, "Good (20 kWh)"),
        (25000, "Excellent (25 kWh)"),
        (32000, "Summer max (32 kWh)"),
    ]

    print("\n=== NEW FORECAST-BASED THRESHOLDS ===\n")
    for forecast_wh, label in test_cases:
        target, reason = get_scaled_soc_target_by_forecast(forecast_wh)
        print(f"{label:30} -> {target:3}%  ({reason})")
