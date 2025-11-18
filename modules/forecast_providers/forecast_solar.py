"""Forecast.Solar forecast provider."""

import logging
from datetime import datetime
from typing import Dict, List, Optional

import requests

from ..api_usage_tracker import record_api_call
from .base import ForecastProvider, ForecastProviderError, NetworkError


class ForecastSolarProvider(ForecastProvider):
    """Forecast.Solar API forecast provider with multi-array support."""

    BASE_URL = "https://api.forecast.solar"
    version = "2.0.0"  # Updated for multi-array support
    requires_api_key = False

    def __init__(self, config):
        """
        Initialize Forecast.Solar provider with support for multiple arrays.

        Args:
            config: Configuration object with:
                - latitude: Site latitude
                - longitude: Site longitude
                - declination: Panel angle (0=horizontal, 90=vertical) - single array
                - azimuth: Panel direction (0=south, 90=west, -90=east) - single array
                - kwp: System size in kW peak - single array
                - arrays: Optional list of ForecastArrayConfig for multi-array setups
                - damping: Damping factor for morning/evening (0-1)
        """
        super().__init__(config)

        self.latitude = getattr(config, "latitude", None)
        self.longitude = getattr(config, "longitude", None)
        self.declination = getattr(config, "declination", 30)
        self.azimuth = getattr(config, "azimuth", 0)
        self.kwp = getattr(config, "kwp", 5.8)
        self.damping = getattr(config, "damping", 0.1)
        self.arrays = getattr(config, "arrays", None)  # Multi-array config

        self.logger = logging.getLogger("growatt-charger")

        if not self.latitude or not self.longitude:
            raise ForecastProviderError(
                "Latitude and longitude must be configured", "Forecast.Solar"
            )

    def get_forecast(self) -> Dict:
        """
        Get solar generation forecast from Forecast.Solar.

        Supports both single-array (uses declination/azimuth/kwp) and
        multi-array configurations (uses arrays list). Each array query
        counts as one API call.

        Returns:
            Dictionary containing forecast data (combined if multi-array)

        Raises:
            NetworkError: If API call fails
        """
        # If arrays are configured, fetch and combine them
        if self.arrays:
            return self._get_multi_array_forecast()
        else:
            return self._get_single_array_forecast()

    def _get_single_array_forecast(self) -> Dict:
        """Fetch forecast for single array configuration."""
        url = (
            f"{self.BASE_URL}/estimate/"
            f"{self.latitude}/{self.longitude}/"
            f"{self.declination}/{self.azimuth}/{self.kwp}"
        )

        params = {}
        if self.damping:
            params["damping"] = self.damping

        try:
            self.logger.debug(f"Fetching single-array forecast from {url}")
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            # Record API call for rate limit tracking
            try:
                rate_remaining = int(response.headers.get("X-Ratelimit-Remaining", 0))
                rate_limit = int(response.headers.get("X-Ratelimit-Limit", 12))
                record_api_call(
                    provider="forecast.solar",
                    endpoint="estimate/single",
                    status_code=response.status_code,
                    quota_remaining=rate_remaining,
                    quota_limit=rate_limit,
                )
                if rate_remaining <= 2:
                    self.logger.warning(
                        f"Forecast.Solar rate limit approaching: {rate_remaining}/{rate_limit} "
                        "calls remaining"
                    )
            except Exception as e:
                self.logger.debug(f"Could not track API usage: {e}")

            return response.json()
        except requests.exceptions.Timeout:
            raise NetworkError("Request timeout", "Forecast.Solar")
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"Request failed: {str(e)}", "Forecast.Solar")

    def _get_multi_array_forecast(self) -> Dict:
        """
        Fetch and combine forecasts for multiple arrays.

        Each array query counts as one API call (Forecast.Solar free tier: 12/hour).
        Forecasts are combined by summing watt-hours for each timestamp.
        """
        if not self.arrays:
            raise ForecastProviderError(
                "Multi-array forecast called but no arrays configured", "Forecast.Solar"
            )

        self.logger.info(
            f"Fetching forecasts for {len(self.arrays)} "
            f"arrays (will use {len(self.arrays)} API calls)"
        )

        all_forecasts = []
        total_kwp = 0

        for idx, array in enumerate(self.arrays, 1):
            self.logger.debug(
                f"  Array {idx}/{len(self.arrays)}: "
                f"declination={array.declination}°, azimuth={array.azimuth}°, kwp={array.kwp}kWp"
            )

            try:
                forecast = self._fetch_array_forecast(array)
                if forecast:
                    all_forecasts.append(
                        {
                            "array_id": idx,
                            "declination": array.declination,
                            "azimuth": array.azimuth,
                            "kwp": array.kwp,
                            "forecast": forecast,
                        }
                    )
                    total_kwp += array.kwp
            except Exception as e:
                self.logger.warning(f"  Failed to fetch array {idx} forecast: {e}")
                continue

        if not all_forecasts:
            raise ForecastProviderError(
                "Could not fetch forecasts for any arrays", "Forecast.Solar"
            )

        # Combine forecasts from all arrays
        combined = self._combine_array_forecasts(all_forecasts, total_kwp)
        return combined

    def _fetch_array_forecast(self, array) -> Optional[Dict]:
        """Fetch forecast for a single array in multi-array setup."""
        url = (
            f"{self.BASE_URL}/estimate/"
            f"{self.latitude}/{self.longitude}/"
            f"{array.declination}/{array.azimuth}/{array.kwp}"
        )

        params = {}
        if self.damping:
            params["damping"] = self.damping

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            # Record API call for rate limit tracking
            try:
                rate_remaining = int(response.headers.get("X-Ratelimit-Remaining", 0))
                rate_limit = int(response.headers.get("X-Ratelimit-Limit", 12))
                record_api_call(
                    provider="forecast.solar",
                    endpoint="estimate/multi-array",
                    status_code=response.status_code,
                    quota_remaining=rate_remaining,
                    quota_limit=rate_limit,
                )
            except Exception as e:
                self.logger.debug(f"Could not track API usage: {e}")

            return response.json()
        except requests.exceptions.Timeout:
            raise NetworkError("Request timeout", "Forecast.Solar")
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"Request failed: {str(e)}", "Forecast.Solar")

    def _combine_array_forecasts(self, forecasts: List[Dict], total_kwp: float) -> Dict:
        """
        Combine forecasts from multiple arrays.

        Sums the watt-hours for each timestamp across all arrays.
        """
        if not forecasts:
            return {}

        combined = {
            "message": "Forecast data for combined multi-array system",
            "result": {
                "watt_hours_day": {},
                "watt_hours_total": 0,
                "watts": {},
            },
            "metadata": {
                "count": len(forecasts),
                "total_kwp": total_kwp,
                "arrays": [
                    {
                        "id": f["array_id"],
                        "declination": f["declination"],
                        "azimuth": f["azimuth"],
                        "kwp": f["kwp"],
                    }
                    for f in forecasts
                ],
            },
        }

        # Collect all timestamps from all arrays
        all_timestamps = set()
        all_dates = set()

        for f in forecasts:
            result = f["forecast"].get("result", {})
            # Collect daily totals
            if "watt_hours_day" in result:
                all_dates.update(result["watt_hours_day"].keys())
            # Collect hourly data
            if "watts" in result:
                all_timestamps.update(result["watts"].keys())

        # Sum watt_hours_day for each date
        for date_str in sorted(all_dates):
            total_wh = 0
            for f in forecasts:
                result = f["forecast"].get("result", {})
                watt_hours_day = result.get("watt_hours_day", {})
                total_wh += watt_hours_day.get(date_str, 0)
            combined["result"]["watt_hours_day"][date_str] = total_wh

        # Sum watts for each timestamp
        for timestamp_str in sorted(all_timestamps):
            total_watts = 0
            for f in forecasts:
                result = f["forecast"].get("result", {})
                watts = result.get("watts", {})
                total_watts += watts.get(timestamp_str, 0)
            combined["result"]["watts"][timestamp_str] = total_watts

        # Calculate total watt-hours
        combined["result"]["watt_hours_total"] = sum(combined["result"]["watt_hours_day"].values())

        return combined

    def get_forecast_for_date(self, target_date: datetime) -> float:
        """
        Get total forecast generation for a specific date in Wh.

        Args:
            target_date: Date to get forecast for

        Returns:
            Total forecasted generation in watt-hours
        """
        forecast_data = self.get_forecast()

        # The API returns 'result' with 'watt_hours_day' containing daily totals
        watt_hours_day = forecast_data.get("result", {}).get("watt_hours_day", {})

        # Format date as YYYY-MM-DD to match API response format
        date_str = target_date.strftime("%Y-%m-%d")

        # Get the forecast for the target date
        forecast_wh = watt_hours_day.get(date_str, 0)

        return float(forecast_wh)

    def get_hourly_forecast_for_date(self, target_date: datetime) -> Dict[datetime, float]:
        """
        Get hourly forecast generation for a specific date.

        Args:
            target_date: Date to get forecast for

        Returns:
            Dictionary mapping datetime to watts for each hour
        """
        forecast_data = self.get_forecast()

        # The API returns 'result' with 'watts' containing hourly data
        watts = forecast_data.get("result", {}).get("watts", {})

        hourly_forecast = {}
        target_date_str = target_date.strftime("%Y-%m-%d")

        for timestamp_str, watts_value in watts.items():
            # Parse timestamp (format: "2025-10-08 14:00:00")
            timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")

            # Only include hours for the target date
            if timestamp.strftime("%Y-%m-%d") == target_date_str:
                hourly_forecast[timestamp] = float(watts_value)

        return hourly_forecast
