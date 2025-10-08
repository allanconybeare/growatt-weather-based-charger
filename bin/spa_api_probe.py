#!/usr/bin/env python3
"""
spa_api_probe.py

Standalone probe for SPA3000TL BL inverter via GrowattServer legacy API.
Logs in, discovers plant_id and device_sn, then calls a suite of test functions.
"""

import os
import logging
import growattServer
import random, string

def setup_logger():
    logger = logging.getLogger("spa-probe")
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))
    logger.addHandler(handler)
    return logger

def test_look_for_spa_system_status(api, device_sn, plant_id, logger):
    """
    Exercise various endpoints for SPA ac-coupled battery in isolation.
    """
    try:
        logger.info(f"Probing SPA/AC system status for SN={device_sn}, Plant ID={plant_id}")

        ## Hypothetical SPA system status <- Not supported in current GrowattServer API
        #if hasattr(api, "spa_system_status"):
        #    resp = api.spa_system_status(device_sn)
        #    logger.info(f"spa_system_status: {resp}")
        #else:
        #    logger.warning("api.spa_system_status() not implemented in wrapper")

        ## Hypothetical AC system status <- Not supported in current GrowattServer API
        #if hasattr(api, "ac_system_status"):
        #    resp = api.ac_system_status(device_sn)
        #    logger.info(f"ac_system_status: {resp}")
        #else:
        #    logger.warning("api.ac_system_status() not implemented in wrapper")

        try:
            # storage_energy_overview sometimes returns useful summary data, including SoC and daily stats <- returns "None" for my SPA3000TL
            resp = api.storage_energy_overview(plant_id, device_sn) 
            logger.info(f"storage_energy_overview: {resp}")
        except Exception as e:
            logger.warning(f"storage_energy_overview failed: {e}")

    except Exception as e:
        logger.error(f"SPA/AC system status test failed: {e}")

def main():
    logger = setup_logger()

    # credentials from env
    username = os.getenv("GROWATT_USERNAME")
    password = os.getenv("GROWATT_PASSWORD")
    if not username or not password:
        logger.error("Please set GROWATT_USERNAME & GROWATT_PASSWORD")
        return

    # random UA just like your main script
    rand_id = ''.join(
       random.choices(string.ascii_uppercase + string.digits,
                      k=random.randint(10,50))
    )
    api = growattServer.GrowattApi(agent_identifier=rand_id)
    api.server_url = "https://server.growatt.com/"

    logger.info("Logging in to Growatt")
    try:
        login_resp = api.login(username, password)
    except Exception as e:
        logger.error(f"Login failed outright: {e}")
        return

    if not login_resp.get("success"):
        logger.error(f"Login rejected: {login_resp}")
        return

    user_id = login_resp["user"]["id"]

    # Discover plant
    plants = api.plant_list(user_id)
    if not plants.get("data"):
        logger.error(f"No plants found for user {user_id}: {plants}")
        return
    plant_id = plants["data"][0]["plantId"]
    logger.info(f"Found Plant ID: {plant_id}")

    # Discover device SN
    plant_info = api.plant_info(plant_id)
    storage_list = plant_info.get("storageList") or []
    if not storage_list:
        logger.error(f"No storage devices in plant {plant_id}: {plant_info}")
        return
    device_sn = storage_list[0]["deviceSn"]
    logger.info(f"Found Device SN: {device_sn}")

    # Run the probe tests
    test_look_for_spa_system_status(api, device_sn, plant_id, logger)

if __name__ == "__main__":
    main()
