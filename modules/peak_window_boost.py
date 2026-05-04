"""Afternoon peak-charge decision logic (14:00 check for 16:00-19:00 peak window)."""

from typing import Dict, Tuple


def should_boost_battery_for_peak_window(
    remaining_forecast_wh: float,
    current_soc: float,
    battery_capacity_wh: float = 6900,
    average_load_w: float = 850,
    peak_window_hours: float = 3.0,
    forecast_reliability: float = 0.4,
    forecast_uncertainty_buffer_pct: float = 10.0,
    minimum_soc_pct: float = 15.0,
) -> Tuple[bool, str, Dict]:
    """
    Decide if battery should be boosted to avoid peak-rate grid import.

    Context:
    - Peak charging window: 16:00–19:00 (3 hours, grid import rates high)
    - Decision time: 14:00 (2 hours before peak starts)
    - Goal: Determine if available solar + current battery can cover peak without drawing from grid

    Logic:
    1. Calculate consumption during peak window (3h × 850W = 2,550 Wh)
    2. Estimate solar generation during peak window (~40% of afternoon forecast)
    3. If solar shortfall > current SOC - safety margin: boost battery

    Args:
        remaining_forecast_wh: Remaining solar generation forecast from 14:00 to sunset (in Wh)
        current_soc: Current battery SOC at 14:00/event run time (%)
        battery_capacity_wh: Battery capacity (default 6900 Wh)
        average_load_w: Average household load (default 850W)
        peak_window_hours: Duration of peak window (default 3.0 hours)
        forecast_reliability: Confidence factor for afternoon forecast (default 0.4, i.e., 40%)
        forecast_uncertainty_buffer_pct: Safety margin or forecast uncertainty buffer (default 10%)
        minimum_soc_pct: Minimum SOC the battery can discharge to (default 15%)

    Returns:
        Tuple of (should_boost: bool, reason: str, details: dict)

    Example:
        >>> should_boost, reason, details = should_boost_battery_for_peak_window(
        ...     remaining_forecast_wh=6000,
        ...     current_soc=35
        ... )
        >>> if should_boost:
        ...     api.update_charge_settings(target_soc=85, charge_rate=50)
    """
    peak_consumption_wh = average_load_w * peak_window_hours

    # Conservative estimate: only ~40% of afternoon forecast reaches peak window
    # (many hours before sunset, clouds in afternoon more common)
    estimated_peak_generation_wh = remaining_forecast_wh * forecast_reliability

    # Calculate shortfall during peak window
    peak_shortfall_wh = max(0, peak_consumption_wh - estimated_peak_generation_wh)
    peak_shortfall_pct = (peak_shortfall_wh / battery_capacity_wh) * 100

    # IMPORTANT: Account for minimum SOC - can't discharge below this
    # Usable battery capacity = current_soc - minimum_soc_pct
    usable_soc = max(0, current_soc - minimum_soc_pct)

    # Required SOC above minimum to cover shortfall with safety margin
    required_soc_above_minimum = peak_shortfall_pct + forecast_uncertainty_buffer_pct

    # Absolute required SOC (including the unusable portion below minimum)
    required_soc_pct = required_soc_above_minimum + minimum_soc_pct

    # Decision: boost if usable SOC insufficient
    should_boost = usable_soc < required_soc_above_minimum

    # Build reason string
    if should_boost:
        reason = (
            f"Boost recommended: Peak window needs {required_soc_above_minimum:.0f}% usable SOC "
            f"(total {required_soc_pct:.0f}% inc {minimum_soc_pct:.0f}% min), "
            f"but only {usable_soc:.0f}% usable available (current {current_soc:.0f}% - "
            f"{minimum_soc_pct:.0f}% min)"
        )
    else:
        reason = (
            f"No boost needed: Peak window needs {required_soc_above_minimum:.0f}% usable SOC, "
            f"current usable {usable_soc:.0f}% is sufficient"
        )

    # Detailed breakdown for logging/analysis
    details = {
        "peak_consumption_wh": peak_consumption_wh,
        "estimated_peak_generation_wh": estimated_peak_generation_wh,
        "peak_shortfall_wh": peak_shortfall_wh,
        "peak_shortfall_pct": peak_shortfall_pct,
        "minimum_soc_pct": minimum_soc_pct,
        "current_soc": current_soc,
        "usable_soc": usable_soc,
        "required_soc_above_minimum": required_soc_above_minimum,
        "required_soc_pct": required_soc_pct,
        "safety_margin_pct": forecast_uncertainty_buffer_pct,
    }

    return should_boost, reason, details


def calculate_peak_window_boost_target(
    remaining_forecast_wh: float,
    current_soc: float,
    battery_capacity_wh: float = 6900,
    average_load_w: float = 850,
    peak_window_hours: float = 3.0,
    forecast_reliability: float = 0.4,
    forecast_uncertainty_buffer_pct: float = 10.0,
    minimum_soc_pct: float = 15.0,
    max_soc: float = 85.0,
) -> Tuple[int, str]:
    """
    Calculate optimal target SOC for afternoon boost.

    Returns the minimum SOC needed to comfortably cover peak window,
    capped at configured maximum.

    Args:
        (same as should_boost_battery_for_peak_window)
        minimum_soc_pct: Minimum SOC the battery can discharge to (default 15%)
        max_soc: Maximum SOC to target (safety limit, default 85%)

    Returns:
        Tuple of (target_soc, reason)
    """
    should_boost, _, details = should_boost_battery_for_peak_window(
        remaining_forecast_wh=remaining_forecast_wh,
        current_soc=current_soc,
        battery_capacity_wh=battery_capacity_wh,
        average_load_w=average_load_w,
        peak_window_hours=peak_window_hours,
        forecast_reliability=forecast_reliability,
        forecast_uncertainty_buffer_pct=forecast_uncertainty_buffer_pct,
        minimum_soc_pct=minimum_soc_pct,
    )

    if not should_boost:
        return int(current_soc), "No boost needed"

    # Target: required SOC + additional buffer (5%) to account for charge efficiency losses
    target_soc = min(max_soc, int(details["required_soc_pct"] + 5))

    reason = (
        f"Boost to {target_soc}% to cover peak window "
        f"(estimated shortfall: {details['peak_shortfall_pct']:.0f}%)"
    )

    return target_soc, reason
