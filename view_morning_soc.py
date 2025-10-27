#!/usr/bin/env python3
"""View morning SOC check results."""

import os
import csv
from datetime import datetime, timedelta


def view_morning_soc_results(days=7):
    """View recent morning SOC check results."""
    soc_file = 'output/morning_soc_checks.csv'
    
    if not os.path.exists(soc_file):
        print("No morning SOC data available yet.")
        print("The morning check runs at 05:00 daily.")
        return
    
    with open(soc_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    if not rows:
        print("No data in morning SOC file yet.")
        return
    
    # Filter to recent days
    if days:
        cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        rows = [r for r in rows if r['Date'] >= cutoff]
    
    print(f"\n{'='*80}")
    print(f"Morning SOC Check Results (Last {days} Days)")
    print(f"{'='*80}\n")
    
    print(f"{'Date':<12} {'Target':<8} {'Actual':<8} {'Variance':<10} {'Rate':<6} {'Achievement':<12} {'Status'}")
    print(f"{'-'*80}")
    
    total_variance = 0
    total_achievement = 0
    count = 0
    
    for row in rows:
        variance = float(row['Variance (%)'])
        achievement = float(row['Achievement (%)'])
        total_variance += abs(variance)
        total_achievement += achievement
        count += 1
        
        # Format variance with color indicator
        if abs(variance) <= 5:
            status_icon = "✓"
        elif abs(variance) <= 10:
            status_icon = "✓"
        elif abs(variance) <= 15:
            status_icon = "⚠"
        else:
            status_icon = "✗"
        
        print(f"{row['Date']:<12} "
              f"{row['Target SOC (%)']+' %':<8} "
              f"{row['Actual SOC (%)']+' %':<8} "
              f"{variance:>+6.1f} %    "
              f"{row['Charge Rate Set (%)']+' %':<6} "
              f"{achievement:>6.1f} %      "
              f"{status_icon} {row['Status']}")
    
    if count > 0:
        avg_variance = total_variance / count
        avg_achievement = total_achievement / count
        
        print(f"{'-'*80}")
        print(f"\nSummary:")
        print(f"  Days tracked: {count}")
        print(f"  Average variance: {avg_variance:.1f}%")
        print(f"  Average achievement: {avg_achievement:.1f}%")
        
        if avg_achievement >= 95:
            print(f"  Status: ✓ Excellent - Charging is highly effective")
        elif avg_achievement >= 85:
            print(f"  Status: ✓ Good - Charging is working well")
        elif avg_achievement >= 75:
            print(f"  Status: ⚠ Fair - Consider reviewing charge rate")
        else:
            print(f"  Status: ✗ Poor - Charging significantly underperforming")
    
    print(f"\n{'='*80}\n")


if __name__ == "__main__":
    import sys
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    view_morning_soc_results(days)
