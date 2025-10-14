# forecast.py
"""""
from forecast_api import get_forecast_data

def get_forecast_for_date(date):
    forecast = get_forecast_data(date)
    return forecast.get("expected_generation_wh", 0)

def compute_scaled_soc(expected_wh):
    # Example scaling logic — adjust as needed
    max_capacity_wh = 10000  # e.g. 10kWh battery
    soc = min(100, int((expected_wh / max_capacity_wh) * 100))
    return soc
"""

"""Solar forecast calculations and SOC target determination."""

from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from .forecast_api import ForecastSolarAPI


def get_scaled_soc_target(
    total_forecast_wh: float,
    battery_capacity_wh: float,
    minimum_charge_pct: int,
    maximum_charge_pct: int,
    average_load_w: float,
    confidence: float = 0.8
) -> int:
    """
    Calculate optimal SOC target based on forecasted solar yield.
    
    The logic is:
    - High forecast: charge less overnight (rely more on solar)
    - Low forecast: charge more overnight (less solar expected)
    
    Args:
        total_forecast_wh: Total forecasted generation for tomorrow in Wh
        battery_capacity_wh: Battery capacity in Wh
        minimum_charge_pct: Minimum allowed charge percentage
        maximum_charge_pct: Maximum allowed charge percentage
        average_load_w: Average household load in watts
        confidence: Confidence factor to apply to forecast (0-1)
        
    Returns:
        Target SOC percentage (constrained by min/max settings)
    """
    # Apply confidence factor to forecast
    adjusted_forecast_wh = total_forecast_wh * confidence
    
    # Calculate what percentage of daily consumption the forecast will cover
    # Assuming 24-hour consumption
    daily_consumption_wh = average_load_w * 24
    
    # How much of daily needs will solar cover?
    solar_coverage_pct = (adjusted_forecast_wh / daily_consumption_wh) * 100
    
    # Determine target SOC based on expected solar coverage
    # These thresholds can be tuned based on your data collection
    if solar_coverage_pct >= 150:  # Excellent solar day
        target_soc = minimum_charge_pct + 10
    elif solar_coverage_pct >= 120:  # Very good solar day
        target_soc = minimum_charge_pct + 20
    elif solar_coverage_pct >= 100:  # Good solar day (covers all needs)
        target_soc = minimum_charge_pct + 30
    elif solar_coverage_pct >= 80:  # Decent solar day
        target_soc = minimum_charge_pct + 40
    elif solar_coverage_pct >= 60:  # Moderate solar day
        target_soc = minimum_charge_pct + 50
    elif solar_coverage_pct >= 40:  # Poor solar day
        target_soc = maximum_charge_pct - 10
    else:  # Very poor solar day
        target_soc = maximum_charge_pct
    
    # Constrain to configured limits
    target_soc = max(minimum_charge_pct, min(maximum_charge_pct, target_soc))
    
    return int(target_soc)


def get_scaled_soc_target_simple(total_forecast_wh: float) -> int:
    """
    Simple threshold-based SOC target calculation.
    This is the function you provided - kept for reference/fallback.
    
    Args:
        total_forecast_wh: Total forecasted generation in Wh
        
    Returns:
        Target SOC percentage
    """
    if total_forecast_wh >= 10000:
        return 30
    elif total_forecast_wh >= 8000:
        return 40
    elif total_forecast_wh >= 7000:
        return 50
    elif total_forecast_wh >= 6000:
        return 60
    elif total_forecast_wh >= 5000:
        return 70
    elif total_forecast_wh >= 4000:
        return 80
    else:
        return 95  # low forecast, fill almost fully


def calculate_charge_rate(
    target_soc: int,
    current_soc: float,
    battery_capacity_wh: float,
    maximum_charge_rate_w: float,
    off_peak_duration_hours: float
) -> int:
    """
    Calculate required charge rate to reach target SOC during off-peak period.
    
    Args:
        target_soc: Target state of charge percentage
        current_soc: Current state of charge percentage
        battery_capacity_wh: Battery capacity in Wh
        maximum_charge_rate_w: Maximum charge rate in watts
        off_peak_duration_hours: Duration of off-peak period in hours
        
    Returns:
        Charge rate as percentage of maximum (0-100)
    """
    # Calculate watt-hours needed
    soc_needed = target_soc - current_soc
    if soc_needed <= 0:
        return 0  # Already at or above target
    
    wh_needed = (soc_needed / 100) * battery_capacity_wh
    
    # Calculate required charge rate
    required_rate_w = wh_needed / off_peak_duration_hours
    
    # Convert to percentage of maximum
    charge_rate_pct = (required_rate_w / maximum_charge_rate_w) * 100
    
    # Constrain to 0-100%
    charge_rate_pct = max(0, min(100, charge_rate_pct))
    
    return int(charge_rate_pct)


class ForecastCalculator:
    """Handles solar forecast calculations and charge planning."""
    
    def __init__(self, api: ForecastSolarAPI, config):
        """
        Initialize forecast calculator.
        
        Args:
            api: ForecastSolarAPI instance
            config: Configuration manager instance
        """
        self.api = api
        self.config = config
    
    def get_tomorrow_forecast(self) -> float:
        """
        Get tomorrow's solar generation forecast.
        
        Returns:
            Forecasted generation in Wh
        """
        tomorrow = datetime.now() + timedelta(days=1)
        return self.api.get_forecast_for_date(tomorrow)
    
    def get_tomorrow_hourly_forecast(self) -> Dict[datetime, float]:
        """
        Get tomorrow's hourly solar generation forecast.
        
        Returns:
            Dictionary mapping hour to forecasted watts
        """
        tomorrow = datetime.now() + timedelta(days=1)
        return self.api.get_hourly_forecast_for_date(tomorrow)
    
    def calculate_optimal_charge_plan(
        self, 
        current_soc: float,
        forecast_wh: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Calculate optimal charging plan based on forecast.
        
        Args:
            current_soc: Current battery charge percentage
            forecast_wh: Optional forecast override (otherwise fetches tomorrow's)
            
        Returns:
            Dictionary containing:
                - target_soc: Target charge percentage
                - charge_rate_pct: Required charge rate percentage
                - forecast_wh: Forecast used for calculation
                - solar_coverage_pct: Percentage of daily needs covered by solar
        """
        # Get forecast if not provided
        if forecast_wh is None:
            forecast_wh = self.get_tomorrow_forecast()
        
        growatt_config = self.config.growatt
        tariff_config = self.config.tariff
        
        # Calculate target SOC
        target_soc = get_scaled_soc_target(
            total_forecast_wh=forecast_wh,
            battery_capacity_wh=growatt_config.battery_capacity_wh,
            minimum_charge_pct=growatt_config.minimum_charge_pct,
            maximum_charge_pct=growatt_config.maximum_charge_pct,
            average_load_w=growatt_config.average_load_w,
            confidence=self.config.forecast.confidence
        )
        
        # Calculate off-peak duration
        start = datetime.strptime(tariff_config.off_peak_start_time, '%H:%M')
        end = datetime.strptime(tariff_config.off_peak_end_time, '%H:%M')
        off_peak_hours = (end - start).seconds / 3600
        
        # Calculate required charge rate
        charge_rate_pct = calculate_charge_rate(
            target_soc=target_soc,
            current_soc=current_soc,
            battery_capacity_wh=growatt_config.battery_capacity_wh,
            maximum_charge_rate_w=growatt_config.maximum_charge_rate_w,
            off_peak_duration_hours=off_peak_hours
        )
        
        # Calculate solar coverage
        daily_consumption_wh = growatt_config.average_load_w * 24
        solar_coverage_pct = (forecast_wh / daily_consumption_wh) * 100
        
        return {
            'target_soc': target_soc,
            'charge_rate_pct': charge_rate_pct,
            'forecast_wh': forecast_wh,
            'solar_coverage_pct': solar_coverage_pct,
            'off_peak_hours': off_peak_hours
        }