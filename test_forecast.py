#!/usr/bin/env python3
"""Test script for solar forecast functionality."""

import os
import sys
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.config import ConfigManager
from modules.forecast_api import get_forecast_data_from_config
from modules.forecast import ForecastCalculator


def main():
    """Test the forecast functionality."""
    print("=" * 60)
    print("Growatt Solar Forecast Test")
    print("=" * 60)
    
    # Load configuration
    config_path = "conf/growatt-charger.ini"
    if not os.path.exists(config_path):
        print(f"Error: Config file not found at {config_path}")
        return 1
    
    try:
        print(f"\n1. Loading configuration from {config_path}...")
        config = ConfigManager(config_path)
        print("   ✓ Configuration loaded successfully")
        
        # Display config
        print(f"\n   System Configuration:")
        print(f"   - Battery capacity: {config.growatt.battery_capacity_wh}Wh")
        print(f"   - Max charge rate: {config.growatt.maximum_charge_rate_w}W")
        print(f"   - Average load: {config.growatt.average_load_w}W")
        print(f"   - Min charge: {config.growatt.minimum_charge_pct}%")
        print(f"   - Max charge: {config.growatt.maximum_charge_pct}%")
        print(f"\n   Solar Array Configuration:")
        print(f"   - Location: {config.forecast.location}")
        print(f"   - System size: {config.forecast.kw_power}kWp")
        print(f"   - Declination: {config.forecast.declination}°")
        print(f"   - Azimuth: {config.forecast.azimuth}°")
        print(f"   - Confidence: {config.forecast.confidence * 100}%")
        
        # Initialize forecast API
        print(f"\n2. Initializing Forecast.Solar API...")
        forecast_api = get_forecast_data_from_config(config)
        print("   ✓ API initialized successfully")
        
        # Get forecast for tomorrow
        print(f"\n3. Fetching tomorrow's forecast...")
        tomorrow = datetime.now() + timedelta(days=1)
        print(f"   Date: {tomorrow.strftime('%Y-%m-%d')}")
        
        forecast_wh = forecast_api.get_forecast_for_date(tomorrow)
        print(f"   ✓ Forecast retrieved: {forecast_wh:.0f}Wh ({forecast_wh/1000:.1f}kWh)")
        
        # Get hourly breakdown
        print(f"\n4. Fetching hourly forecast...")
        hourly = forecast_api.get_hourly_forecast_for_date(tomorrow)
        
        if hourly:
            print(f"   Hourly breakdown ({len(hourly)} hours):")
            for hour, watts in sorted(hourly.items()):
                print(f"   - {hour.strftime('%H:%M')}: {watts:>6.0f}W")
        else:
            print("   No hourly data available")
        
        # Test charge plan calculation
        print(f"\n5. Testing charge plan calculation...")
        calculator = ForecastCalculator(forecast_api, config)
        
        # Test with different current SOC levels
        test_soc_levels = [20, 40, 60, 80]
        
        print(f"\n   Testing different current SOC levels:")
        print(f"   {'-' * 55}")
        print(f"   Current | Target | Rate | Solar Coverage")
        print(f"   SOC (%) | SOC(%) | (%)  | (%)")
        print(f"   {'-' * 55}")
        
        for current_soc in test_soc_levels:
            charge_plan = calculator.calculate_optimal_charge_plan(
                current_soc=current_soc,
                forecast_wh=forecast_wh
            )
            
            print(f"   {current_soc:>7} | {charge_plan['target_soc']:>6} | "
                  f"{charge_plan['charge_rate_pct']:>4} | "
                  f"{charge_plan['solar_coverage_pct']:>6.1f}")
        
        print(f"   {'-' * 55}")
        
        # Detailed breakdown for current real SOC
        print(f"\n6. Detailed charge plan for current battery state...")
        print(f"   (Assuming current SOC is 50% for this test)")
        
        charge_plan = calculator.calculate_optimal_charge_plan(
            current_soc=50.0,
            forecast_wh=forecast_wh
        )
        
        print(f"\n   Forecast Summary:")
        print(f"   - Tomorrow's generation: {charge_plan['forecast_wh']:.0f}Wh "
              f"({charge_plan['forecast_wh']/1000:.2f}kWh)")
        print(f"   - Solar coverage: {charge_plan['solar_coverage_pct']:.1f}% of daily needs")
        
        print(f"\n   Charging Plan:")
        print(f"   - Target SOC: {charge_plan['target_soc']}%")
        print(f"   - Charge rate: {charge_plan['charge_rate_pct']}%")
        print(f"   - Off-peak duration: {charge_plan['off_peak_hours']:.1f} hours")
        
        # Calculate energy to charge
        soc_needed = charge_plan['target_soc'] - 50.0
        wh_needed = (soc_needed / 100) * config.growatt.battery_capacity_wh
        
        print(f"\n   Energy Transfer:")
        print(f"   - SOC increase needed: {soc_needed:.1f}%")
        print(f"   - Energy to charge: {wh_needed:.0f}Wh ({wh_needed/1000:.2f}kWh)")
        
        if wh_needed > 0:
            charge_time = charge_plan['off_peak_hours']
            avg_charge_rate = wh_needed / charge_time
            print(f"   - Average charge rate: {avg_charge_rate:.0f}W")
        
        # Show interpretation
        print(f"\n7. Interpretation:")
        coverage = charge_plan['solar_coverage_pct']
        
        if coverage >= 150:
            print("   📊 Excellent solar forecast!")
            print("   → Minimal overnight charging recommended")
            print("   → System will rely primarily on solar generation")
        elif coverage >= 100:
            print("   📊 Good solar forecast")
            print("   → Moderate overnight charging")
            print("   → Solar should cover most daily needs")
        elif coverage >= 60:
            print("   📊 Moderate solar forecast")
            print("   → Increased overnight charging recommended")
            print("   → Solar will supplement grid charging")
        else:
            print("   📊 Poor solar forecast")
            print("   → Maximum overnight charging recommended")
            print("   → System will rely heavily on battery reserves")
        
        print(f"\n{'=' * 60}")
        print("✓ All tests completed successfully!")
        print(f"{'=' * 60}\n")
        
        return 0
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())