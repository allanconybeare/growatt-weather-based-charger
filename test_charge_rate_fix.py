#!/usr/bin/env python
"""Test the charge rate calculation fix."""

from modules.forecast import calculate_charge_rate

print("CHARGE RATE CALCULATION FIX - IMPACT ANALYSIS")
print("=" * 70)
print()

# Test various scenarios
scenarios = [
    {"name": "Excellent Solar Day", "target": 50, "current": 20, "reason": "High forecast"},
    {"name": "Good Solar Day", "target": 65, "current": 35, "reason": "Decent forecast"},
    {"name": "Fair Solar Day", "target": 80, "current": 30, "reason": "Moderate forecast"},
    {"name": "Poor Solar Day (Nov 13)", "target": 85, "current": 44, "reason": "Low forecast"},
    {"name": "Very Poor Solar Day", "target": 95, "current": 10, "reason": "Minimal forecast"},
]

for scenario in scenarios:
    target = scenario["target"]
    current = scenario["current"]

    # Old calculation (no consumption)
    soc_needed = target - current
    wh_needed_old = (soc_needed / 100) * 6900
    old_rate = int((wh_needed_old / 2.983) / 3000 * 100)

    # New calculation (with consumption)
    new_rate = calculate_charge_rate(
        target_soc=target,
        current_soc=current,
        battery_capacity_wh=6900,
        maximum_charge_rate_w=3000,
        off_peak_duration_hours=2.983,
        average_load_w=850,
    )

    improvement = new_rate - old_rate
    pct_increase = (improvement / old_rate * 100) if old_rate > 0 else 0

    print(f"{scenario['name']}:")
    print(f"  Current: {current}% -> Target: {target}% ({scenario['reason']})")
    print(
        f"  OLD rate: {old_rate}% | "
        f"NEW rate: {new_rate}% | "
        f"Difference: +{improvement}pp (+{pct_increase:.0f}%)"
    )
    print()

print("KEY INSIGHT:")
print("  - Worst impact on POOR days (when accurate calculation matters most)")
print("  - Nov 13 went from 31% to 59% (28pp improvement)")
print("  - Now accounts for house consumption during charging window")
