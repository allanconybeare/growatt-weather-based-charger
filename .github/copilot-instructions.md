## Quick context

This repository implements a small utility to calculate and apply overnight charging plans
for Growatt inverters using solar generation forecasts. Main pieces:

- `src/app.py` - main orchestration: loads config, initializes `GrowattAPI`, `ForecastManager`,
  `ForecastCalculator` and `DataLogger`, then computes and (optionally) applies charging settings.
- `modules/forecast_providers/` - provider implementations (registry in `manager.py`). Add new
  providers here and register them in `ForecastManager.PROVIDERS`.
- `modules/forecast.py` - forecast-to-SOC logic: `get_scaled_soc_target`, `calculate_charge_rate`,
  and `ForecastCalculator` (used by `src/app.py`).
- `modules/growatt_api.py` (and `modules/growatt_session.py`) - Growatt API wrappers used to
  login, fetch device/status and push charge schedules.
- `conf/growatt-charger.ini` and `defaults/growatt-charger-default.ini` - INI configuration used
  by the app; environment variables may be used for secrets (e.g. `GROWATT_USERNAME`,
  `GROWATT_PASSWORD`, `SOLCAST_API_KEY`).

## Practical guidance for AI coding agents

Keep instructions concrete and tied to files. Avoid generic edits — prefer small, testable changes.

- When changing how forecasts are consumed or adding a provider:
  - Implement a class under `modules/forecast_providers/` that follows the existing provider
    interface (see `base.py`). Required capabilities: `get_forecast_for_date()`,
    `get_hourly_forecast_for_date()`, and `test_connection()`.
  - Update the provider registry in `modules/forecast_providers/manager.py` (the `PROVIDERS` map).
  - Run `pytest test_providers.py` to exercise provider selection/fallback behaviour.

- When adjusting charge calculation rules:
  - Make changes in `modules/forecast.py` (functions `get_scaled_soc_target` and
    `calculate_charge_rate`). `ForecastCalculator.calculate_optimal_charge_plan` consumes
    those functions and returns a dict used by `src/app.py`.
  - Keep outputs stable: `target_soc` is an int %, `charge_rate_pct` is an int 0-100, and
    `forecast_wh` is a numeric Wh value.

- When touching Growatt API code:
  - Use `modules/growatt_api.py` / `modules/growatt_session.py` interfaces. Typical methods
    used by the app: `login`, `get_system_status(device_sn, plant_id)`, `get_plant_info`, and
    `update_charge_settings(...)`. Preserve exception classes used by `src/app.py`.

## Role & Expertise
- Be an elite software developer with expertise in Python, command-line tools, and file system operations.
- Excel at debugging complex issues and optimizing code performance.

## Code Style
- Always use classes instead of standalone functions for Python code.

## Dependency Management
- Always use UV for installing dependencies to ensure consistency and efficiency.

## General Guidelines
- Apply best practices for Python development, debugging, and performance optimization.
- Reference project technology stack and requirements as needed.

## Run / debug / test commands (PowerShell on Windows)

- Create a venv and install deps:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

- Run the main app (from project root):

```powershell
python -m src.app conf\growatt-charger.ini
# Or use the provided wrapper scripts: run_growatt_charger.bat (Windows) or Dockerfile image
```

- Run tests:

```powershell
pytest -q
```

## Important repo-specific conventions

- Config is INI-based (see `conf/growatt-charger.ini`). `ConfigManager` (used in `src/app.py`)
  exposes grouped attributes (`growatt`, `tariff`, `forecast`, `solcast`) and code expects
  typed attributes (e.g. `battery_capacity_wh` numeric, `off_peak_start_time` string `HH:MM`).
- Multi-provider pattern: `ForecastManager` accepts a comma-separated list from config and will
  initialise providers from the `PROVIDERS` registry; `primary_provider` is used for charge
  decisions and `log_all_providers` toggles comparison logging.
- Logging and outputs go to `logs/` and `output/` under project root; Dockerized runs use
  `/opt/growatt-charger/{logs,conf,output}` so prefer path-agnostic code using project root.

## Integration & external dependencies

- Forecast providers: `forecast.solar` (forecast.solar) and `solcast` (Solcast API). Keep in mind
  `forecast.solar` has a free-tier rate limit — avoid frequent calls in tests or CI.
- Growatt integration uses the `growattServer` library (see `requirements.txt`). Do not embed
  credentials in repo; prefer environment variables `GROWATT_USERNAME`, `GROWATT_PASSWORD`.

## Example quick tasks (with files to edit)

- Add a Solcast fallback tweak: edit `modules/forecast_providers/solcast.py` and
  `modules/forecast_providers/manager.py` to prefer resource_id when available.
- Change target SOC thresholds: edit `modules/forecast.py` -> `get_scaled_soc_target` and
  update unit tests that assert expected SOC boundaries.

## Safety notes for agents

- Don't commit real credentials. If you must run with credentials, prefer environment vars.
- Preserve exit codes and exceptions used by `src/app.py` (the app relies on specific exception
  classes to decide retry/fallback behavior).

---

If any part of this is unclear or you'd like more detail (examples of adding a provider, a
short test to assert forecasting behaviour, or a CI workflow), tell me which area to expand.
