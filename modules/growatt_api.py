# growatt_api.py

from growatt_session import get_session, call_endpoint

def get_current_soc():
    session = get_session()
    response = call_endpoint(session, "/device/soc")
    return response.get("soc", 0)

def get_daily_generation():
    session = get_session()
    response = call_endpoint(session, "/device/daily")
    return response.get("generation_wh", 0)

def push_charge_schedule(soc_target):
    session = get_session()
    payload = {
        "mode": "manual",
        "target_soc": soc_target,
        "start_time": "00:00",
        "end_time": "23:59"
    }
    result = call_endpoint(session, "/device/set_schedule", payload)
    return result.get("success", False)
