"""Forecast.Solar forecast provider."""

import logging
from datetime import datetime
from typing import Dict, List, Optional

import requests

from ..api_usage_tracker import can_make_calls, record_api_call
from ..forecast_cache import ForecastCache
from .base import (
    ForecastProvider,
    ForecastProviderError,
    NetworkError,
    RateLimitError,
)

# Don't create module-level logger - get it in __init__ instead
# logger = logging.getLogger(__name__)


class ForecastSolarProvider(ForecastProvider):
    """Forecast.Solar API forecast provider with multi-array support."""

    BASE_URL = "https://api.forecast.solar"
    version = "2.0.0"
    requires_api_key = False

    def __init__(self, config, cache: Optional[ForecastCache] = None):
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
            cache: Optional ForecastCache instance for caching API responses
        """
        super().__init__(config)

        # Get logger as child of root logger (will inherit configured handlers)
        # self.logger = logging.getLogger("growatt-charger.forecast_solar")
        # Use module name - automatically inherits from configured root logger
        self.logger = logging.getLogger(__name__)

        # Set up API Response cache
        self.cache = cache  # Injected cache instance

        self.latitude = getattr(config, "latitude", None)
        self.longitude = getattr(config, "longitude", None)
        self.declination = getattr(config, "declination", 30)
        self.azimuth = getattr(config, "azimuth", 0)
        self.kwp = getattr(config, "kwp", 5.8)
        self.damping = getattr(config, "damping", 0.1)
        self.arrays = getattr(config, "arrays", None)

        if not self.latitude or not self.longitude:
            raise ForecastProviderError(
                "Latitude and longitude must be configured", "Forecast.Solar"
            )

    def get_forecast(self) -> Dict:
        """
        Get solar generation forecast from Forecast.Solar.
        Get forecast, using cache if available.

        Supports both single-array (uses declination/azimuth/kwp) and
        multi-array configurations (uses arrays list). Each array query
        counts as one API call.

        Returns:
            Dictionary containing forecast data (combined if multi-array)

        Raises:
            NetworkError: If API call fails
            RateLimitError: If quota exhausted
        """

        target_date = datetime.now()  # or tomorrow depending on your logic

        # Try cache first
        if self.cache:
            # Build array config for cache key
            array_config = None
            if self.arrays:
                array_config = {
                    "arrays": [
                        {"declination": a.declination, "azimuth": a.azimuth, "kwp": a.kwp}
                        for a in self.arrays
                    ]
                }
            cached = self.cache.get("forecast.solar", target_date, array_config)
            if cached:
                self.logger.info("Using cached Forecast.Solar data")
                return cached

        # Fetch from API
        if self.arrays:
            data = self._get_multi_array_forecast()
        else:
            data = self._get_single_array_forecast()

        # Store in cache
        if self.cache:
            array_config = None
            if self.arrays:
                array_config = {
                    "arrays": [
                        {"declination": a.declination, "azimuth": a.azimuth, "kwp": a.kwp}
                        for a in self.arrays
                    ]
                }
            self.cache.set("forecast.solar", target_date, data, array_config)

        return data

    @staticmethod
    def _safe_int(value, default):
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _read_rate_limit(self, response, data, default_limit, default_remaining):
        limit_header = response.headers.get("X-Ratelimit-Limit")
        remain_header = response.headers.get("X-Ratelimit-Remaining")

        limit = self._safe_int(limit_header, None)
        remaining = self._safe_int(remain_header, None)

        if limit is None or remaining is None:
            self.logger.warning("No rate limit info in response headers, checking body")
            message = data.get("message", {})
            block = message.get("ratelimit", {})
            if limit is None:
                limit = self._safe_int(block.get("limit"), default_limit)
            if remaining is None:
                remaining = self._safe_int(block.get("remaining"), default_remaining)

        return limit, remaining

    def _get_single_array_forecast(self) -> Dict:
        """Fetch forecast for single array configuration."""
        self.logger.debug("Fetching single-array forecast")

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
            data = response.json()

            # Record API call for rate limit tracking
            try:
                rate_limit, rate_remaining = self._read_rate_limit(
                    response, data, default_limit=12, default_remaining=0
                )

                self.logger.info(
                    f"Single array fetch complete - Rate limit: {rate_remaining}/"
                    f"{rate_limit} remaining"
                )
                self.logger.debug(f"Data: {data}")

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
                self.logger.error(f"Could not track API usage: {e}")

            return data

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

        # PRE-FLIGHT CHECK: Do we have quota for all arrays?
        num_calls = len(self.arrays)
        can_proceed, reason = can_make_calls("forecast.solar", num_calls=num_calls)
        if not can_proceed:
            self.logger.warning(f"Insufficient quota for {num_calls} arrays: {reason}")
            raise RateLimitError(reason, "Forecast.Solar")

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
                forecast = self._fetch_array_forecast(array, idx)
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
        self.logger.info(
            f"Combined forecast from {len(all_forecasts)} arrays: "
            f"{combined['result']['watt_hours_total']:.0f}Wh total"
        )
        return combined

    def _fetch_array_forecast(self, array, array_idx: int = 0) -> Optional[Dict]:
        """
        Fetch forecast for a single array in multi-array setup.

        Note: Quota checking is done once in _get_multi_array_forecast()
        before calling this method, so no need to check again here.
        """
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
            data = response.json()

            self.logger.debug(f"DEBUG: url: {url} params: {params} ")
            self.logger.debug(f"DEBUG: Data: {data}")

            # Record API call for rate limit tracking
            try:
                rate_limit, rate_remaining = self._read_rate_limit(
                    response, data, default_limit=12, default_remaining=0
                )

                self.logger.info(
                    f"Array {array_idx} fetch complete - "
                    f"Rate limit: {rate_remaining}/{rate_limit} remaining"
                )

                record_api_call(
                    provider="forecast.solar",
                    endpoint="estimate/multi-array",
                    status_code=response.status_code,
                    quota_remaining=rate_remaining,
                    quota_limit=rate_limit,
                )

                if rate_remaining <= 2:
                    self.logger.warning(
                        f"Forecast.Solar rate limit critical: {rate_remaining}/"
                        f"{rate_limit} remaining"
                    )
            except Exception as e:
                self.logger.error(f"Could not track API usage: {e}")

            return data

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
            if "watt_hours_day" in result:
                all_dates.update(result["watt_hours_day"].keys())
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
