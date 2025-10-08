# forecast.py

from forecast_api import get_forecast_data

def get_forecast_for_date(date):
    forecast = get_forecast_data(date)
    return forecast.get("expected_generation_wh", 0)

def compute_scaled_soc(expected_wh):
    # Example scaling logic — adjust as needed
    max_capacity_wh = 10000  # e.g. 10kWh battery
    soc = min(100, int((expected_wh / max_capacity_wh) * 100))
    return soc
