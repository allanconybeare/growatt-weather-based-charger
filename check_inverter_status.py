#!/usr/bin/env python3
"""
Inverter status check script.

Checks whether the Growatt inverter is online and operating normally.
Designed to be run as a scheduled task (e.g., every hour or every few hours)
so that a tripped switch on the solar board is detected quickly rather than
going unnoticed for days.

Exit codes:
  0 - Inverter is online and operating normally
  1 - Inverter is offline, lost communication, or in a fault state
  2 - Script error (API failure, config problem, etc.)
"""

import csv
import os
import sys
from datetime import datetime

from modules.email_notifier import EmailNotifier
from src.api import GrowattAPI
from src.config import ConfigManager
from src.utils import setup_logging

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Growatt storage device status codes
# Numeric deviceStatus codes returned in the Growatt storageList API response.
# Confirmed against a real SPA3000 AC-coupled device.
DEVICE_STATUS = {
    0: "Standby / Waiting",
    1: "Normal (On-Grid)",
    2: "Discharging",
    3: "Fault",
    4: "Flash / Updating",
    5: "Charging (AC/Grid)",
    6: "Charging (Solar/Normal)",
    7: "Check",
    8: "Off-Grid (switch tripped)",
}

# deviceStatus codes that mean the inverter is NOT operating normally.
# 3 = hardware fault, 8 = off-grid (solar board switch tripped).
PROBLEM_STATUS_CODES = {3, 8}


class InverterStatusChecker:
    """Checks inverter online/offline status and logs results."""

    def __init__(self, config_path: str):
        self.config_path = config_path
        log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
        self.logger = setup_logging(
            log_dir=log_dir,
            log_file="inverter-status-check.log",
            additional_fields={"script": "inverter-status-check"},
            config_path=config_path,
        )

        config_dir = os.path.dirname(os.path.abspath(config_path))
        project_root = os.path.dirname(config_dir)
        self.output_dir = os.path.join(project_root, "output")
        os.makedirs(self.output_dir, exist_ok=True)

    def run(self) -> int:
        """
        Run the inverter status check.

        Returns:
            0 if inverter is online and healthy
            1 if inverter is offline, lost, or faulted
            2 if the check itself failed (API/config error)
        """
        self.logger.info("Starting inverter status check...")

        try:
            config = ConfigManager(self.config_path)
        except Exception as e:
            self.logger.error(f"Failed to load config: {e}")
            return 2

        try:
            api = GrowattAPI()
            growatt_config = config.growatt

            self.logger.info("Logging in to Growatt API...")
            api.login(growatt_config.username, growatt_config.password)

            # Resolve plant/device IDs
            if growatt_config.plant_id and growatt_config.device_sn:
                plant_id = growatt_config.plant_id
                device_sn = growatt_config.device_sn
            else:
                device_info = api.get_device_info()
                plant_id = device_info["plant_id"]
                device_sn = device_info["device_sn"]

            self.logger.info(f"Checking device {device_sn} at plant {plant_id}")

            # Fetch raw plant info to read the storageList entry directly.
            # This gives us the 'lost' flag and numeric 'status' code that are
            # not surfaced through get_system_status().
            plant_info = api.get_plant_info(plant_id)
            storage_list = plant_info.get("storageList", [])
            raw_device = next(
                (d for d in storage_list if d.get("deviceSn", "").upper() == device_sn.upper()),
                None,
            )

            # Also fetch the richer status dict (SOC etc.)
            try:
                system_status = api.get_system_status(device_sn, plant_id)
            except Exception as e:
                self.logger.warning(f"get_system_status failed: {e}")
                system_status = {}

            # --- Determine online / offline state ---
            is_lost = False
            status_code = None
            soc = None
            last_update = None

            if raw_device:
                # 'lost' == True means the inverter has stopped communicating with the cloud.
                is_lost = bool(raw_device.get("lost", False))

                # deviceStatus is the key field for this device (returned as a string).
                raw_status = raw_device.get("deviceStatus")
                if raw_status is not None:
                    try:
                        status_code = int(raw_status)
                    except (ValueError, TypeError):
                        status_code = None

                last_update = raw_device.get("lastUpdateTime") or raw_device.get("last_update_time")

            if system_status:
                soc = system_status.get("SOC")

            status_text = (
                DEVICE_STATUS.get(status_code, f"Unknown (code {status_code})")
                if status_code is not None
                else "Unknown"
            )

            # --- Classify the result ---
            if is_lost:
                health = "OFFLINE"
                is_healthy = False
                detail = (
                    "Device has lost communication with the Growatt cloud "
                    "(inverter may be switched off or disconnected)"
                )
            elif status_code in PROBLEM_STATUS_CODES:
                if status_code == 8:
                    health = "OFF-GRID"
                    detail = (
                        f"Inverter is off-grid (deviceStatus={status_code}: {status_text}). "
                        "The solar board switch has likely tripped — check and reset it."
                    )
                else:
                    health = "FAULT"
                    detail = (
                        f"Inverter reported a fault (deviceStatus={status_code}: {status_text})"
                    )
                is_healthy = False
            elif status_code is None:
                health = "UNKNOWN"
                is_healthy = False
                detail = "Could not read deviceStatus from API response"
            else:
                health = "ONLINE"
                is_healthy = True
                detail = status_text

            # --- Log to CSV ---
            self._log_status(
                device_sn=device_sn,
                plant_id=plant_id,
                health=health,
                status_code=status_code,
                status_text=status_text,
                soc=soc,
                is_lost=is_lost,
                last_update=last_update,
            )

            # --- Print summary ---
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n{'='*60}")
            print(f"Inverter Status Check - {now}")
            print(f"{'='*60}")
            print(f"Device SN : {device_sn}")
            print(f"Plant ID  : {plant_id}")
            print(f"Health    : {health}")
            print(f"Mode      : {status_text} (deviceStatus={status_code})")
            if soc is not None:
                print(f"Battery SOC: {soc}%")
            if last_update:
                print(f"Last update: {last_update}")
            print(f"{'='*60}")

            if is_healthy:
                print("Result: OK - Inverter is operating normally\n")
                self.logger.info(f"Inverter healthy - {health}: {detail}")
                return 0
            else:
                print(f"Result: ALERT - {detail}\n")
                self.logger.warning(f"Inverter problem detected - {health}: {detail}")
                self._send_alert_email(
                    config, health, detail, status_code, status_text, soc, device_sn
                )
                return 1

        except Exception as e:
            self.logger.error(f"Inverter status check failed with an unexpected error: {e}")
            import traceback

            traceback.print_exc()
            return 2

    def _send_alert_email(
        self,
        config,
        health: str,
        detail: str,
        status_code,
        status_text: str,
        soc,
        device_sn: str,
    ) -> None:
        """Send an alert email if email notifications are enabled."""
        try:
            email_config = config.email
        except Exception as e:
            self.logger.warning(f"Could not load email config, skipping alert: {e}")
            return

        if not email_config.enabled:
            self.logger.debug("Email notifications disabled - skipping alert")
            return

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        subject = f"[Solar Alert] Inverter {health} - {device_sn}"

        soc_plain = f"Battery   : {soc}%\n" if soc is not None else ""
        plain = (
            f"Inverter Status Alert\n"
            f"{'='*40}\n"
            f"Time      : {now}\n"
            f"Device SN : {device_sn}\n"
            f"Health    : {health}\n"
            f"Mode      : {status_text} (deviceStatus={status_code})\n"
            f"{soc_plain}"
            f"\nDetail:\n{detail}\n"
            f"\nThis alert was generated by the Growatt inverter status check."
        )

        html = (
            f"<h2 style='color:red'>&#9888; Inverter Status Alert</h2>"
            f"<table style='border-collapse:collapse;font-family:sans-serif'>"
            f"<tr><td style='padding:4px 12px 4px 0'><b>Time</b></td>"
            f"<td>{now}</td></tr>"
            f"<tr><td style='padding:4px 12px 4px 0'><b>Device SN</b></td>"
            f"<td>{device_sn}</td></tr>"
            f"<tr><td style='padding:4px 12px 4px 0'><b>Health</b></td>"
            f"<td style='color:red'><b>{health}</b></td></tr>"
            f"<tr><td style='padding:4px 12px 4px 0'><b>Mode</b></td>"
            f"<td>{status_text} (deviceStatus={status_code})</td></tr>"
            + (
                f"<tr><td style='padding:4px 12px 4px 0'><b>Battery SOC</b></td>"
                f"<td>{soc}%</td></tr>"
                if soc is not None
                else ""
            )
            + f"</table>"
            f"<p>{detail}</p>"
            f"<p style='color:grey;font-size:small'>Sent by Growatt inverter status check</p>"
        )

        notifier = EmailNotifier.from_config(email_config)
        sent = notifier.send_alert(subject, plain, html)
        if sent:
            print(f"Alert email sent to {email_config.recipient_email}")
        else:
            print("WARNING: Failed to send alert email - check logs for details")

    def _log_status(
        self,
        device_sn: str,
        plant_id: str,
        health: str,
        status_code,
        status_text: str,
        soc,
        is_lost: bool,
        last_update,
    ) -> None:
        """Append a status record to output/inverter_status_checks.csv."""
        csv_path = os.path.join(self.output_dir, "inverter_status_checks.csv")
        file_exists = os.path.isfile(csv_path)

        with open(csv_path, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(
                    [
                        "Check Time",
                        "Device SN",
                        "Plant ID",
                        "Health",
                        "Status Code",
                        "Status Text",
                        "Battery SOC (%)",
                        "Lost",
                        "Last Inverter Update",
                    ]
                )

            writer.writerow(
                [
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    device_sn,
                    plant_id,
                    health,
                    status_code if status_code is not None else "",
                    status_text,
                    soc if soc is not None else "",
                    is_lost,
                    last_update or "",
                ]
            )


def main() -> int:
    config_path = os.getenv("GROWATT_CONFIG", "conf/growatt-charger.ini")

    if not os.path.exists(config_path):
        print(f"ERROR: Config file not found: {config_path}", file=sys.stderr)
        return 2

    checker = InverterStatusChecker(config_path)
    return checker.run()


if __name__ == "__main__":
    sys.exit(main())
