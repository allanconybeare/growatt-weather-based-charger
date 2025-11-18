# Growatt Inverter Solar Forecast Configuration Assistant

A tool for configuring overnight charging for Growatt inverters with batteries, based on solar generation forecasts. Automatically charges your battery during off-peak periods to minimize grid import during expensive peak hours.

**⚡ Quick Start**: [Read the documentation](docs/README.md) – Complete setup guides and reference material

## What It Does

- 🌤️ **Predicts solar generation** using [forecast.solar](https://forecast.solar/) or [Solcast](https://www.solcast.com.au/)
- 🔋 **Calculates optimal charge settings** to maximize off-peak charging
- ⏰ **Schedules battery boost** before afternoon peak rates (if needed)
- 📊 **Logs performance** to track SOC, generation, and charging decisions
- 🎯 **Works with Growatt inverters** via [PyPi growattServer](https://github.com/indykoning/PyPi_GrowattServer)

## Usage
This software can be run either as a Docker container or directly from the source code. Log files are written to:
- When running in Docker: `/opt/growatt-charger/logs/growatt-charger.log`
- When running from source: `<project_root>/logs/growatt-charger.log`

The scripts do not contain any sort of loop, therefore you can run them as (in)frequently as you like, NOTE: There is a limit on the free tier of forecast.solar meaning that if you make more than 12 calls per hour you will be blocked temporarily until your rate limit resets

An example of how to run the container (breakdown below):
```
sudo docker run --rm -e TZ=Europe/London -v ${PWD}/conf:/opt/growatt-charger/conf -v ${PWD}/output:/opt/growatt-charger/output -v ${PWD}/logs:/opt/growatt-charger/logs muppet3000/growatt-charger:latest
```

Arguments explained:
```
--rm - Remove the container once the run is complete

-e TZ=Europe/London - Replace this with your timezone, full list here: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones (use the TZ database name column)

-v ${PWD}/conf:/opt/growatt-charger/conf - Maps a local directory (the current directory, with a new sub-dir 'conf') through to the container for configuration

-v ${PWD}/output:/opt/growatt-charger/output - Maps a local directory (the current directory, with a new sub-dir 'output') through to the container for the simple text output

-v ${PWD}/logs:/opt/growatt-charger/logs - Maps a local directory (the current directory, with a new sub-dir 'conf') through to the container for logs to be outputted to
```

Note - it is not mandatory to map through the `logs` and `output` directory if you don't need them.

## 📖 Documentation

See **[docs/README.md](docs/README.md)** for comprehensive guides and reference material:

- **[Setup Guides](docs/guides/)** – Initial setup, configuration, deployment
- **[Technical Reference](docs/reference/)** – Architecture, charging logic, calculations
- **[Archive](docs/archive/)** – Historical notes and session logs

### Common Starting Points

| I want to... | Read |
|---|---|
| Configure peak window settings | [Peak Window Config Guide](docs/guides/PEAK_WINDOW_CONFIG_GUIDE.md) |
| Add a forecast provider | [Multi-Provider Setup](docs/guides/multi_provider_setup_guide.md) |
| Understand battery charging | [Charge Rate Analysis](docs/reference/BATTERY_HEALTH_AND_CHARGE_RATE_ANALYSIS.md) |
| Deploy to production | [Deployment Guide](docs/guides/DEPLOYMENT_READY.md) |

## Getting Started

### Option 1: Docker (Recommended)

```bash
docker run --rm \
  -e TZ=Europe/London \
  -v ${PWD}/conf:/opt/growatt-charger/conf \
  -v ${PWD}/logs:/opt/growatt-charger/logs \
  muppet3000/growatt-charger:latest
```

### Option 2: From Source

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\Activate.ps1 on Windows
pip install -r requirements.txt
python -m src.app conf/growatt-charger.ini
```

### Configure Credentials

Use environment variables (recommended):
```bash
export GROWATT_USERNAME=your_username
export GROWATT_PASSWORD=your_password
export SOLCAST_API_KEY=your_key  # if using Solcast
```

Or edit `conf/growatt-charger.ini` (less secure)

## Configuration Highlights

Key settings in `conf/growatt-charger.ini`:

| Setting | Description |
|---------|-------------|
| `battery_capacity_wh` | Battery size in Wh (e.g., 9900 for 9.9kWh) |
| `average_load_w` | House consumption in Watts (e.g., 850W) |
| `off_peak_start_time` | When cheap rates begin (e.g., 02:00) |
| `off_peak_end_time` | When cheap rates end (e.g., 05:00) |
| `peak_start_time` | When expensive rates begin (e.g., 16:00) |
| `peak_end_time` | When expensive rates end (e.g., 19:00) |
| `location` | Your address or coordinates |
| `kw_power` | Solar panel capacity (e.g., 6.1kW) |

See [docs/guides/PEAK_WINDOW_CONFIG_GUIDE.md](docs/guides/PEAK_WINDOW_CONFIG_GUIDE.md) for details.

## How It Works
