#!/usr/bin/env python

import random
import string
import sys
import os
import configparser
import growattServer

def main():
    print("Testing Growatt settings update...")

    # Load config
    cfg = configparser.ConfigParser()
    cfg_file = "conf/growatt-charger.ini"
    if not os.path.exists(cfg_file):
        print(f"Error: Config file not found at {cfg_file}")
        sys.exit(1)
    cfg.read(cfg_file)

    # Get credentials
    growatt_cfg = cfg["growatt"]
    username = growatt_cfg.get("username") or os.getenv("GROWATT_USERNAME")
    password = growatt_cfg.get("password") or os.getenv("GROWATT_PASSWORD")

    if not username or not password:
        print("Error: Missing Growatt credentials")
        sys.exit(1)

    # Initialize API
    rand_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=random.randint(1,50)))
    api = growattServer.GrowattApi(agent_identifier=rand_id)
    api.server_url = "https://server.growatt.com/"

    print("Logging in...")
    login_resp = api.login(username, password)
    if not login_resp.get("success"):
        print("Error: Growatt login failed")
        sys.exit(1)
    print("Login successful")

    # Get plant and device info
    print("Getting device info...")
    plant_list = api.plant_list(login_resp['user']['id'])
    plant_id = plant_list['data'][0]['plantId']
    plant_info = api.plant_info(plant_id)
    
    device_sn = None
    if 'storageList' in plant_info and plant_info['storageList']:
        device_sn = plant_info['storageList'][0]['deviceSn']
    print(f"Device SN: {device_sn}")
    print(f"Plant ID: {plant_id}")
    print(f"Plant info: {plant_info}")

    # Test settings update
    # Setting battery charge to 80% between 2:00-4:59 
    params = {
        "param1": "80",      # Charge rate %
        "param2": "100",     # Stop SOC
        "param3": "02",      # Start hour (slot 1)
        "param4": "00",      # Start minute (slot 1)
        "param5": "04",      # End hour (slot 1)
        "param6": "59",      # End minute (slot 1)
        "param7": "1",       # Enable slot 1
        "param8": "00",      # Start hour (slot 2)
        "param9": "00",      # Start minute (slot 2)
        "param10": "00",     # End hour (slot 2)
        "param11": "00",     # End minute (slot 2)
        "param12": "0",      # Disable slot 2
        "param13": "00",     # Start hour (slot 3)
        "param14": "00",     # Start minute (slot 3)
        "param15": "00",     # End hour (slot 3)
        "param16": "00",     # End minute (slot 3)
        "param17": "0"       # Disable slot 3
    }

    print("\nTesting AC-coupled settings update...")
    try:
        response = api.update_ac_inverter_setting(
            device_sn,
            "spa_ac_charge_time_period",  # Using the exact endpoint from the original code
            params
        )
        print(f"Settings update response: {response}")
    except Exception as e:
        print(f"Error updating settings: {e}")

if __name__ == "__main__":
    main()