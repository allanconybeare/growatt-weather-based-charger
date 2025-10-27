#!/usr/bin/env python3
"""View and compare forecast provider accuracy."""

import os
import csv
from datetime import datetime, timedelta
from typing import Dict, List
from src.config import ConfigManager
from modules.forecast_providers import ForecastManager


def load_provider_forecasts() -> List[Dict]:
    """Load provider forecast comparisons."""
    comp_file = 'output/provider_comparison.csv'
    
    if not os.path.exists(comp_file):
        return []
    
    with open(comp_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)


def load_actuals() -> Dict[str, float]:
    """Load actual generation data."""
    actuals_file = 'output/actuals.csv'
    
    if not os.path.exists(actuals_file):
        return {}
    
    actuals = {}
    with open(actuals_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            date = row['Date']
            gen_kwh = float(row['Actual Generation (kWh)'])
            actuals[date] = gen_kwh
    
    return actuals

def calculate_accuracy(forecast_kwh: float, actual_kwh: float) -> float:
    """Calculate forecast accuracy percentage."""
    if actual_kwh == 0:
        return 0.0
    return (forecast_kwh / actual_kwh) * 100

# Helper to get config path
# TODO: Move to common utils module
def getConfigPath() -> str:
    import os
    # Get config path from environment or use default
    config_path = os.getenv(
        'GROWATT_CONFIG',
        '/opt/growatt-charger/conf/growatt-charger.ini'
    )
    
    # Also check for local config file
    if not os.path.exists(config_path):
        local_config = 'conf/growatt-charger.ini'
        if os.path.exists(local_config):
            config_path = local_config
    return config_path

def view_provider_comparison(days=14):
    """Display provider comparison and accuracy analysis."""
    print(f"\n{'='*90}")
    print(f"Forecast Provider Comparison & Accuracy (Last {days} Days)")
    print(f"{'='*90}\n")
    
    # Load configuration
    config_path = getConfigPath()
    config = ConfigManager(config_path)
    providers_config = config.forecast_providers
    #print(f"Primary provider: {providers_config.primary_provider}")

    # Load data
    forecasts = load_provider_forecasts()
    actuals = load_actuals()
    
    if not forecasts:
        print("No provider comparison data available yet.")
        print("Multi-provider logging will start when app runs at 22:00.")
        return
    
    # Filter to recent days
    if days:
        cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        forecasts = [f for f in forecasts if f['Date'] >= cutoff]
    
    # Display comparison table
    print(f"{'Date':<12} {'Primary':<10} {'Solcast':<10} {'F.Solar':<10} {'Actual':<10} {'Variance'}")
    print(f"{'-'*90}")
    
    solcast_accuracies = []
    fsolar_accuracies = []
    
    for row in forecasts:
        date = row['Date']
        primary = row['Primary Provider']
        solcast_fc = row['Solcast Forecast (kWh)']
        fsolar_fc = row['ForecastSolar Forecast (kWh)']
        variance = row['Variance (%)']
        
        # Get actual
        actual = actuals.get(date)
        actual_str = f"{actual:.2f} kWh" if actual else "Pending"
        
        # Calculate accuracies
        if actual:
            if solcast_fc != "N/A":
                solcast_acc = calculate_accuracy(float(solcast_fc), actual)
                solcast_accuracies.append(solcast_acc)
                error = abs(solcast_acc - 100)
                solcast_str = f"{solcast_fc} ({error:.0f}% err)"
            else:
                solcast_str = "N/A"
            
            if fsolar_fc != "N/A":
                fsolar_acc = calculate_accuracy(float(fsolar_fc), actual)
                fsolar_accuracies.append(fsolar_acc)
                error = abs(fsolar_acc - 100)
                fsolar_str = f"{fsolar_fc} ({error:.0f}% err)"
            else:
                fsolar_str = "N/A"
        else:
            solcast_str = solcast_fc if solcast_fc != "N/A" else "N/A"
            fsolar_str = fsolar_fc if fsolar_fc != "N/A" else "N/A"
        
        # Format primary indicator
        primary_marker = "→" if primary == providers_config.primary_provider else " "
        
        print(f"{date:<12} {primary_marker}{primary:<9} {solcast_str:<18} {fsolar_str:<18} {actual_str:<10} {variance}%")
    
    # Summary statistics
    if solcast_accuracies or fsolar_accuracies:
        print(f"\n{'-'*90}")
        print(f"\nProvider Accuracy Summary:")
        print(f"{'-'*40}")
        
        if solcast_accuracies:
            avg_solcast = sum(solcast_accuracies) / len(solcast_accuracies)
            print(f"Solcast:")
            print(f"  Average Accuracy: {avg_solcast:.1f}%")
            print(f"  Best: {max(solcast_accuracies):.1f}%")
            print(f"  Worst: {min(solcast_accuracies):.1f}%")
            print(f"  Days: {len(solcast_accuracies)}")
        
        if fsolar_accuracies:
            avg_fsolar = sum(fsolar_accuracies) / len(fsolar_accuracies)
            print(f"\nForecast.Solar:")
            print(f"  Average Accuracy: {avg_fsolar:.1f}%")
            print(f"  Best: {max(fsolar_accuracies):.1f}%")
            print(f"  Worst: {min(fsolar_accuracies):.1f}%")
            print(f"  Days: {len(fsolar_accuracies)}")
        
        # Recommendation
        if solcast_accuracies and fsolar_accuracies:
            print(f"\n{'-'*40}")
            print(f"Comparison:")
            
            # Calculate average error (distance from 100%)
            avg_solcast_error = abs(avg_solcast - 100)
            avg_fsolar_error = abs(avg_fsolar - 100)
            
            diff = avg_solcast_error - avg_fsolar_error
            
            if abs(diff) < 5:
                print(f"  Both providers perform similarly")
                print(f"  Solcast avg error: {avg_solcast_error:.1f}%")
                print(f"  Forecast.Solar avg error: {avg_fsolar_error:.1f}%")
            elif avg_solcast_error < avg_fsolar_error:
                print(f"  ✓ Solcast is more accurate")
                print(f"  Solcast avg error: {avg_solcast_error:.1f}%")
                print(f"  Forecast.Solar avg error: {avg_fsolar_error:.1f}%")
                if providers_config.primary_provider == 'solcast':
                    print(f"  Recommendation: Keep Solcast as primary")
                else:
                    print(f"  Recommendation: Consider switching to Solcast as primary")
            else:
                print(f"  ✓ Forecast.Solar is more accurate")
                print(f"  Solcast avg error: {avg_solcast_error:.1f}%")
                print(f"  Forecast.Solar avg error: {avg_fsolar_error:.1f}%")
                if providers_config.primary_provider == 'forecast.solar':
                    print(f"  Recommendation: Keep Forecast.Solar as primary")
                else:
                    print(f"  Recommendation: Consider switching to Forecast.Solar as primary")
    else:
        print(f"\nInsufficient data for accuracy comparison.")
        print(f"Need at least one matched forecast-to-actual datapoint.")
    
    print(f"\n{'='*90}\n")


if __name__ == "__main__":
    import sys
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 14
    view_provider_comparison(days)