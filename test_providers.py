#!/usr/bin/env python3
"""Test script for multi-provider forecast system."""

import os
import sys
from datetime import datetime, timedelta

# Add to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.config import ConfigManager
from modules.forecast_providers import ForecastManager


def print_header(title):
    """Print formatted header."""
    print(f"\n{'='*70}")
    print(f"{title:^70}")
    print(f"{'='*70}\n")


def test_providers():
    """Test all configured forecast providers."""
    print_header("Multi-Provider Forecast Test")
    
    # Load configuration
    config_path = "conf/growatt-charger.ini"
    if not os.path.exists(config_path):
        print(f"Error: Config file not found at {config_path}")
        return 1
    
    try:
        print("1. Loading configuration...")
        config = ConfigManager(config_path)
        print("   ✓ Configuration loaded")
        
        # Show provider configuration
        providers_config = config.forecast_providers
        print(f"\n   Configured Providers: {', '.join(providers_config.providers)}")
        print(f"   Primary Provider: {providers_config.primary_provider}")
        print(f"   Fallback Enabled: {providers_config.fallback_enabled}")
        print(f"   Log All Providers: {providers_config.log_all_providers}")
        
        # Initialize forecast manager
        print(f"\n2. Initializing forecast providers...")
        manager = ForecastManager(
            config,
            providers=providers_config.providers,
            primary_provider=providers_config.primary_provider
        )
        print(f"   ✓ Initialized {len(manager.providers)} provider(s)")
        
        # Test connections
        print(f"\n3. Testing provider connections...")
        test_results = manager.test_all_providers()
        
        for provider_name, success in test_results.items():
            status = "✓ OK" if success else "✗ FAILED"
            print(f"   {provider_name}: {status}")
        
        if not any(test_results.values()):
            print("\n   ✗ All providers failed!")
            return 1
        
        # Get tomorrow's forecast from all providers
        tomorrow = datetime.now() + timedelta(days=1)
        print(f"\n4. Fetching forecasts for {tomorrow.strftime('%Y-%m-%d')}...")
        
        all_forecasts = manager.get_all_forecasts_for_date(tomorrow)
        
        print(f"\n   {'Provider':<20} {'Forecast':<15} {'Status'}")
        print(f"   {'-'*50}")
        
        for provider_name, forecast_wh in all_forecasts.items():
            if forecast_wh is not None:
                forecast_kwh = forecast_wh / 1000
                status = "✓"
                print(f"   {provider_name:<20} {forecast_kwh:>6.2f} kWh      {status}")
            else:
                print(f"   {provider_name:<20} {'ERROR':<15} ✗")
        
        # Compare forecasts if multiple providers
        if len([f for f in all_forecasts.values() if f is not None]) > 1:
            print(f"\n5. Forecast Comparison:")
            valid_forecasts = {k: v for k, v in all_forecasts.items() if v is not None}
            
            if len(valid_forecasts) >= 2:
                forecasts_list = list(valid_forecasts.values())
                avg_forecast = sum(forecasts_list) / len(forecasts_list)
                max_forecast = max(forecasts_list)
                min_forecast = min(forecasts_list)
                variance = max_forecast - min_forecast
                variance_pct = (variance / avg_forecast * 100) if avg_forecast > 0 else 0
                
                print(f"   Average: {avg_forecast/1000:.2f} kWh")
                print(f"   Range: {min_forecast/1000:.2f} - {max_forecast/1000:.2f} kWh")
                print(f"   Variance: {variance/1000:.2f} kWh ({variance_pct:.1f}%)")
                
                if variance_pct < 10:
                    print(f"   ✓ Providers agree closely")
                elif variance_pct < 25:
                    print(f"   ⚠ Moderate disagreement between providers")
                else:
                    print(f"   ✗ Significant disagreement - check configuration")
        
        # Get hourly breakdown from primary provider
        print(f"\n6. Hourly breakdown (from {manager.primary_provider_name})...")
        try:
            hourly, provider_used = manager.get_hourly_forecast_for_date(tomorrow)
            
            if hourly:
                print(f"   Using: {provider_used}")
                print(f"\n   {'Time':<10} {'Generation'}")
                print(f"   {'-'*25}")
                
                for hour, watts in sorted(hourly.items())[:12]:  # Show first 12 hours
                    print(f"   {hour.strftime('%H:%M'):<10} {watts:>8.0f} W")
                
                if len(hourly) > 12:
                    print(f"   ... ({len(hourly) - 12} more hours)")
            else:
                print("   No hourly data available")
        except Exception as e:
            print(f"   ✗ Failed to get hourly data: {e}")
        
        # Summary
        print(f"\n{'='*70}")
        print("✓ All tests completed successfully!")
        print(f"{'='*70}\n")
        
        # Recommendations
        print("Recommendations:")
        if len(manager.providers) == 1:
            print("  • Single provider mode - consider adding a backup provider")
        else:
            print("  • Multi-provider mode active")
            print("  • Monitor accuracy over time using view_performance.py")
        
        print(f"\nPrimary provider ({manager.primary_provider_name}) will be used for charging decisions.")
        
        return 0
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(test_providers())
