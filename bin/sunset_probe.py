from datetime import datetime, timedelta
from modules.growatt_logging import log_run_to_csv
from modules.growatt_api import get_current_soc, get_daily_generation, push_charge_schedule
from modules.forecast import get_forecast_for_date, compute_scaled_soc
from modules.sunset import get_sunset_time, update_sunset_job

def run_sunset_probe():
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")

    # 1. Get actual SOC and generation
    sunset_soc = get_current_soc()
    actual_generation_wh = get_daily_generation()

    # 2. Log today's performance
    log_run_to_csv(
        date=today_str,
        sunset_soc=sunset_soc,
        actual_generation_wh=actual_generation_wh
    )

    # 3. Get tomorrow’s forecast and compute SOC
    tomorrow = now + timedelta(days=1)
    forecast = get_forecast_for_date(tomorrow)
    scaled_soc = compute_scaled_soc(forecast)

    # 4. Push schedule to inverter
    push_charge_schedule(scaled_soc)

    # 5. Get tomorrow’s sunset time and update job
    sunset_time = get_sunset_time(tomorrow)
    update_sunset_job(sunset_time)
