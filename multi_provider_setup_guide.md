# Multi-Provider Forecast Setup Guide

## 🎯 Overview

Your system now supports multiple forecast providers with automatic fallback and comparison capabilities. This allows you to:
- Use the most accurate provider (Solcast)
- Have a backup if the primary fails
- Compare accuracy between providers over time
- Switch providers easily

## 📦 What's New

### New Files Created
```
modules/forecast_providers/
├── __init__.py          # Package initialization
├── base.py              # Base provider interface
├── solcast.py           # Solcast implementation
├── forecast_solar.py    # Forecast.Solar implementation
└── manager.py           # Multi-provider manager
```

### New Scripts
- `test_providers.py` - Test all configured providers

## 🔧 Setup Instructions

### Step 1: Set Environment Variable

Set your Solcast API key as an environment variable:

**Windows PowerShell (Permanent):**
```powershell
[System.Environment]::SetEnvironmentVariable('SOLCAST_API_KEY', 'your_api_key_here', 'User')
```

**Verify:**
```powershell
$env:SOLCAST_API_KEY
```

**Note**: Restart VS Code after setting the environment variable.

### Step 2: Update Configuration File

Add to your `conf/growatt-charger.ini`:

```ini
[forecast.solar]
location = 51.913599,0.855471
declination = 30
azimuth = 0
kw_power = 5.8
damping = 0.1
confidence = 0.8

# Multi-provider configuration
providers = solcast,forecast.solar
primary_provider = solcast
fallback_enabled = true
log_all_providers = true

[solcast]
# API key from environment variable SOLCAST_API_KEY - 
#  create an account on solcast, in your profile generate the key
# Optional: Use resource_id for higher accuracy, required if using the free tier
# Comma-separated list of resource IDs for multiple azimuth's; solcast "supports" split arrays 
#  or multiple azimuth's by using multiple locations e.g. -
#  You have panels facing in multiple directions
#  https://kb.solcast.com.au/how-do-i-create-a-multiple-azimuth-rooftop-solar-site
# resource_id = d367-4a1c-0d79-32b9, d367-4a1c-0d79-64b1
```

### Step 3: Create Provider Directories

```powershell
# Create the forecast_providers directory
New-Item -ItemType Directory -Path modules\forecast_providers -Force
```

### Step 4: Add the Files

Copy the new files into your project:
1. `modules/forecast_providers/__init__.py`
2. `modules/forecast_providers/base.py`
3. `modules/forecast_providers/solcast.py`
4. `modules/forecast_providers/forecast_solar.py`
5. `modules/forecast_providers/manager.py`
6. `test_providers.py` (in root directory)

### Step 5: Update Config Module

Add the new properties to `src/config/configuration.py` (from the config_with_providers artifact).

### Step 6: Test the Setup

```bash
python test_providers.py
```

Expected output:
```
==================================================================
            Multi-Provider Forecast Test
==================================================================

1. Loading configuration...
   ✓ Configuration loaded

   Configured Providers: solcast, forecast.solar
   Primary Provider: solcast
   Fallback Enabled: True

2. Initializing forecast providers...
   ✓ Initialized 2 provider(s)

3. Testing provider connections...
   solcast: ✓ OK
   forecast.solar: ✓ OK

4. Fetching forecasts for 2025-10-14...

   Provider             Forecast        Status
   --------------------------------------------------
   solcast                8.50 kWh      ✓
   forecast.solar        12.30 kWh      ✓

5. Forecast Comparison:
   Average: 10.40 kWh
   Range: 8.50 - 12.30 kWh
   Variance: 3.80 kWh (36.5%)
   ⚠ Moderate disagreement between providers
```

## 🎛️ Configuration Modes

### Mode 1: Solcast Only (Recommended after testing)
```ini
providers = solcast
primary_provider = solcast
```
- Uses only Solcast
- Most accurate
- Limited to 10 API calls/day

### Mode 2: Multi-Provider Comparison (Recommended for initial testing)
```ini
providers = solcast,forecast.solar
primary_provider = solcast
log_all_providers = true
```
- Fetches from both providers
- Uses Solcast for decisions
- Logs both for comparison
- Uses 1 Solcast call/day

### Mode 3: Forecast.Solar Only (Fallback)
```ini
providers = forecast.solar
primary_provider = forecast.solar
```
- Uses only Forecast.Solar
- Unlimited calls
- Less accurate in UK weather

### Mode 4: Solcast with Automatic Fallback
```ini
providers = solcast,forecast.solar
primary_provider = solcast
fallback_enabled = true
log_all_providers = false
```
- Tries Solcast first
- Falls back to Forecast.Solar if Solcast fails
- Only logs the provider that was actually used

## 📊 Data Logging

When `log_all_providers = true`, the system will:
1. Log forecasts from all providers in `predictions.csv`
2. Create a new file `provider_comparison.csv` showing accuracy per provider
3. Display provider performance in `view_performance.py`

**predictions.csv** will include:
```csv
..., Provider, Forecast (Wh), Alternative Forecasts
..., solcast, 8500, {"forecast.solar": 12300}
```

## 🔍 Monitoring & Analysis

### View Current Forecasts
```bash
python test_providers.py
```

### Compare Provider Accuracy (after a few days)
```bash
python view_performance.py
```

Will show accuracy breakdown per provider:
```
Provider Performance:
  Solcast: 92.3% average accuracy
  Forecast.Solar: 68.5% average accuracy
```

## ⚙️ Advanced: Resource ID Setup

For maximum accuracy, configure your Solcast resource ID:

1. Log into Solcast
2. Go to your Rooftop Sites
3. Copy your Resource ID
4. Add to config:
```ini
[solcast]
resource_id = d367-4a1c-0d79-32b9
```

This uses your exact panel specifications for more accurate forecasts.

## 🐛 Troubleshooting

### "Solcast API key not configured"
- Check environment variable: `$env:SOLCAST_API_KEY`
- Restart VS Code after setting environment variable

### "RateLimitError: API rate limit exceeded"
- Solcast free tier: 10 calls/day
- System uses 1 call/day at 22:00
- If testing frequently, switch to forecast.solar temporarily

### "NetworkError: Request failed"
- Check internet connection
- Verify API key is correct
- Check Solcast service status

### Both providers return very different forecasts
- Normal for UK variable weather
- Solcast usually more accurate
- Monitor over 1-2 weeks to see patterns

## 📈 Expected Results

After switching to Solcast, you should see:
- Forecast accuracy improve from ~30% to ~80-90%
- Better charging decisions on variable weather days
- More realistic forecasts (7-12 kWh vs 17+ kWh)

## 🎯 Recommended Settings

**For UK October/Winter:**
```ini
[forecast.solar]
damping = 0.3              # Higher for low sun angles
confidence = 0.8           # Keep as-is
providers = solcast        # Use only Solcast after testing
primary_provider = solcast
```

## 🚀 Next Steps

1. **Set up environment variable**
2. **Run test_providers.py** - Verify both providers work
3. **Use multi-provider mode** for 1 week to compare
4. **Review accuracy** with view_performance.py
5. **Switch to Solcast only** if accuracy is better
6. **Fine-tune** based on collected data

Your system is now ready for multi-provider forecasting! 🌤️📊
