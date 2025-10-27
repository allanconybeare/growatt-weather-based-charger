"""Utility functions for Growatt charger calculations."""

from datetime import datetime
from typing import Dict, Optional, Union


def get_grid_neutral_time(average_load_w: float, generation_forecast: Dict[datetime, float]) -> Optional[datetime]:
    """
    Find the time when generation exceeds average load.
    
    Args:
        average_load_w: Average load in watts
        generation_forecast: Dictionary of datetime to forecast watt-hours
        
    Returns:
        datetime when generation exceeds load, or None if never grid neutral
    """
    for hour, forecast in generation_forecast.items():
        if int(forecast) > average_load_w:
            return hour
    return None


def get_grid_neutral_wh(
    grid_neutral_time: datetime,
    today_off_peak_end: datetime,
    average_load_w: float
) -> float:
    """
    Calculate watt-hours needed to reach grid neutral time.
    
    Args:
        grid_neutral_time: Time when generation exceeds load
        today_off_peak_end: When off-peak rate ends
        average_load_w: Average load in watts
        
    Returns:
        Watt-hours needed to reach grid neutral
    """
    # Calculate duration on battery
    duration = datetime.combine(datetime.min, grid_neutral_time.time()) - \
              datetime.combine(datetime.min, today_off_peak_end.time())
    hours = duration.seconds/3600
    return hours * average_load_w


def get_surplus_generation_for_battery(
    generation_forecast: Dict[datetime, float],
    average_load_w: float,
    maximum_charge_rate_w: float
) -> float:
    """
    Calculate surplus generation available for battery charging.
    
    Args:
        generation_forecast: Dictionary of datetime to forecast watt-hours
        average_load_w: Average load in watts
        maximum_charge_rate_w: Maximum charging rate in watts
        
    Returns:
        Total surplus watt-hours available for battery
    """
    surplus_generation_for_battery = 0
    for forecast in generation_forecast.values():
        if forecast > average_load_w:
            hour_to_battery = forecast - average_load_w
            if hour_to_battery > maximum_charge_rate_w:
                hour_to_battery = maximum_charge_rate_w
            surplus_generation_for_battery += hour_to_battery
    return surplus_generation_for_battery


def get_offpeak_duration(off_peak_start: str, off_peak_end: str) -> float:
    """
    Calculate duration of off-peak period in hours.
    
    Args:
        off_peak_start: Start time as HH:MM
        off_peak_end: End time as HH:MM
        
    Returns:
        Duration in hours
        
    Raises:
        ValueError: If start time is after end time
    """
    start_time = datetime.strptime(off_peak_start, '%H:%M')
    end_time = datetime.strptime(off_peak_end, '%H:%M')
    
    if start_time > end_time:
        raise ValueError("Off-peak start time is after end time")
        
    duration = end_time - start_time
    return duration.seconds/3600  # Convert seconds to hours
