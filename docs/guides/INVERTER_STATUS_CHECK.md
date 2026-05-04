# Inverter Status Check

Monitors the Growatt inverter at regular intervals and sends an alert if it goes offline or into a fault state. Designed to catch the common scenario where a switch on the solar board trips undetected, stopping solar energy from reaching the batteries for days at a time.

---

## How It Works

The check script (`check_inverter_status.py`) connects to the Growatt cloud API and reads the `deviceStatus` field from the inverter's storage entry. It classifies the result and exits with a code that Task Scheduler can act on:

| Exit code | Meaning |
|-----------|---------|
| `0` | Inverter is online and operating normally |
| `1` | Inverter is offline, off-grid, or faulted — alert sent |
| `2` | Script error (API failure, config problem) |

### Detected conditions

| `deviceStatus` | Health label | What it means |
|----------------|-------------|---------------|
| 6 | `ONLINE` | Charging from solar — normal daytime operation |
| 0, 1, 2, 5, 7 | `ONLINE` | Standby / discharging / other normal states |
| 8 | `OFF-GRID` | Solar board switch has tripped — no generation reaching batteries |
| 3 | `FAULT` | Hardware fault reported by inverter |
| — | `OFFLINE` | Inverter has lost communication with the Growatt cloud |

Results are appended to `output/inverter_status_checks.csv` on every run for historical review.

---

## Files

| File | Purpose |
|------|---------|
| `check_inverter_status.py` | Main check script |
| `run_inverter_status_check.bat` | Wrapper used by Task Scheduler (handles logging, optional toast notification) |
| `create_inverter_status_task.ps1` | One-time setup script to register the Windows Scheduled Task |
| `test_email.py` | Unit tests for email config and notifier; `--live` flag sends a real test email |
| `modules/email_notifier.py` | SMTP email sending module (used by the check script) |

---

## Setup

### 1. Configure email alerts (optional but recommended)

Edit `conf/growatt-charger.ini` and set up the `[email]` section:

```ini
[email]
enabled = true
smtp_port = 587

# Use environment variables for credentials (recommended):
#   SMTP_SERVER, SENDER_EMAIL, SENDER_PASSWORD, SENDER_NAME, RECIPIENT_EMAIL
#
# Or set them directly here:
# smtp_server = smtp.gmail.com
# sender_email = you@gmail.com
# sender_password = your-app-password
# sender_name = Solar Tracker
# recipient_email = you@example.com
```

> **Gmail users**: you must use an [App Password](https://myaccount.google.com/apppasswords), not your normal account password. Two-factor authentication must be enabled on the account first.

Test your email configuration before setting up the scheduled task:

```powershell
python test_email.py --live
```

### 2. Register the scheduled task

Open PowerShell **as Administrator** and run:

```powershell
cd C:\path\to\growatt-weather-based-charger
.\create_inverter_status_task.ps1
```

This creates a task named `GrowattInverterStatusCheck` that runs every **2 hours between 06:00 and 22:00** daily. `StartWhenAvailable = true` means a missed check runs as soon as the PC wakes up.

### 3. Verify it works

Trigger a manual run immediately:

```powershell
Start-ScheduledTask -TaskName "GrowattInverterStatusCheck"
```

Check the result:

```powershell
Get-ScheduledTaskInfo -TaskName "GrowattInverterStatusCheck" | Select-Object LastRunTime, LastTaskResult
```

`LastTaskResult = 0` = healthy. `1` = alert triggered. Also check the log:

```
logs\inverter_status_check.log
```

---

## Alert notifications

When a problem is detected the script sends:

1. **Email alert** — subject `[Solar Alert] Inverter OFF-GRID - <device_sn>` with device details and a plain-text + HTML body pointing at the solar board switch.
2. **Windows toast / message box** — only if the notification block in `run_inverter_status_check.bat` is uncommented (requires a logged-in user session).

> The email fires regardless of whether anyone is logged in. The toast only appears in an interactive desktop session.

---

## Adjusting the schedule

To change the check frequency, re-run `create_inverter_status_task.ps1` after editing the `<Repetition><Interval>` value in the XML. Common values:

| Interval | Meaning |
|----------|---------|
| `PT1H` | Every 1 hour |
| `PT2H` | Every 2 hours (default) |
| `PT4H` | Every 4 hours |

---

## Running manually

```powershell
# From project root with venv active:
python check_inverter_status.py
```

The `GROWATT_CONFIG` environment variable overrides the default config path:

```powershell
$env:GROWATT_CONFIG = "C:\custom\path\growatt-charger.ini"
python check_inverter_status.py
```

---

## Output files

| File | Contents |
|------|---------|
| `logs/inverter_status_check.log` | Timestamped log of every check run |
| `output/inverter_status_checks.csv` | CSV history: check time, health, deviceStatus, SOC, lost flag |
