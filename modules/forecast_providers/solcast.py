"""Solcast solar forecast provider."""

from datetime import datetime
from typing import Dict, Optional

import requests

from ..api_usage_tracker import get_global_tracker, get_quota_status, record_api_call
from .base import (
    AuthenticationError,
    ForecastProvider,
    ForecastProviderError,
    NetworkError,
    RateLimitError,
)


class SolcastProvider(ForecastProvider):
    """Solcast API forecast provider."""

    BASE_URL = "https://api.solcast.com.au"
    version = "1.0.0"
    requires_api_key = True

    def __init__(self, config):
        """
        Initialize Solcast provider.

        Args:
            config: Configuration object with:
                - api_key: Solcast API key
                - resource_id: Single resource ID or comma-separated list
                - latitude: Site latitude
                - longitude: Site longitude
                - azimuth: Panel azimuth (Forecast.Solar format: 0=South)
        """
        super().__init__(config)

        # Get Solcast-specific config
        self.api_key = getattr(config, "api_key", None)
        resource_id_str = getattr(config, "resource_id", None)

        # Parse resource IDs (can be comma-separated for multiple arrays)
        if resource_id_str:
            self.resource_ids = [rid.strip() for rid in resource_id_str.split(",")]
        else:
            self.resource_ids = []

        # Fallback to main forecast config for location
        self.latitude = getattr(config, "latitude", None)
        self.longitude = getattr(config, "longitude", None)

        # Convert azimuth from Forecast.Solar format to Solcast format
        # Forecast.Solar: 0=South, 90=West, -90=East, -180=North
        # Solcast: 0=North, 90=West, -90=East, 180=South
        forecast_solar_azimuth = getattr(config, "azimuth", 0)
        self.azimuth = self._convert_azimuth(forecast_solar_azimuth)

        self.tilt = getattr(
            config, "declination", 30
        )  # Solcast uses 'tilt' instead of 'declination'
        self.capacity = getattr(config, "kwp", 5.8)

        if not self.api_key:
            raise ForecastProviderError("Solcast API key not configured", "Solcast")

        # Resource IDs are optional - if not provided, we'll use lat/lon
        # (but lat/lon requires paid tier)
        if not self.resource_ids and (not self.latitude or not self.longitude):
            raise ForecastProviderError(
                "Either resource_id or latitude/longitude must be configured", "Solcast"
            )

    @property
    def resource_id(self):
        """Backwards compatibility property for single resource_id access."""
        return self.resource_ids[0] if self.resource_ids else None

    def _convert_azimuth(self, forecast_solar_azimuth: float) -> float:
        """
        Convert azimuth from Forecast.Solar format to Solcast format.

        Forecast.Solar: -180=North, -90=East, 0=South, 90=West
        Solcast: 0=North, -90=East, 180/-180=South, 90=West

        Args:
            forecast_solar_azimuth: Azimuth in Forecast.Solar format

        Returns:
            Azimuth in Solcast format
        """
        # Simple conversion: add 180 degrees, then normalize to [-180, 180]
        solcast_azimuth = forecast_solar_azimuth + 180

        # Normalize to [-180, 180]
        if solcast_azimuth > 180:
            solcast_azimuth -= 360

        return solcast_azimuth

    def _make_request(self, endpoint: str, params: Dict = None) -> Dict:
        """
        Make an authenticated request to Solcast API.

        Args:
            endpoint: API endpoint path
            params: Query parameters

        Returns:
            JSON response

        Raises:
            Various ForecastProviderError subclasses
        """
        url = f"{self.BASE_URL}/{endpoint}"
        headers = {"Authorization": f"Bearer {self.api_key}", "Accept": "application/json"}

        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)

            # Extract rate limit information from response headers
            quota_limit = self._get_header_int(response, "x-rate-limit-limit")
            quota_remaining = self._get_header_int(response, "x-rate-limit-remaining")

            # Log rate limit information (before checking for errors)
            self._log_rate_limit_info(response)

            # Determine error message if present
            error_msg = None
            if response.status_code == 429:
                error_msg = "Rate limit exceeded (10 calls/day)"
            elif response.status_code == 401:
                error_msg = "Invalid API key"
            elif response.status_code >= 400:
                error_msg = f"HTTP {response.status_code}"

            # Record API call for usage tracking (including failed calls)
            try:
                record_api_call(
                    provider="solcast",
                    endpoint=endpoint,
                    status_code=response.status_code,
                    quota_remaining=quota_remaining,
                    quota_limit=quota_limit,
                    error=error_msg,
                )
            except Exception as e:
                # Don't let tracking errors break API calls
                import logging

                logger = logging.getLogger(__name__)
                logger.debug(f"Failed to record API usage: {str(e)}")

            # Check for rate limiting
            if response.status_code == 429:
                # Log detailed warning about quota exhaustion
                import logging

                logger = logging.getLogger("growatt-charger")
                reset_dt = None
                if quota_remaining is not None:
                    reset_header = response.headers.get("x-rate-limit-reset")
                    if reset_header:
                        try:
                            reset_dt = datetime.fromtimestamp(int(reset_header))
                            logger.warning(
                                "Solcast quota exhausted! Cannot make more calls "
                                f"until {reset_dt.strftime('%Y-%m-%d %H:%M:%S')} UTC. "
                                f"Remaining: {quota_remaining}, "
                                f"Reset: {reset_dt.strftime('%Y-%m-%d %H:%M:%S')}"
                            )
                        except (ValueError, TypeError):
                            pass
                raise RateLimitError("API rate limit exceeded (10 calls/day)", "Solcast")

            # Check for authentication errors
            if response.status_code == 401:
                raise AuthenticationError("Invalid API key", "Solcast")

            # Check for other errors
            response.raise_for_status()

            return response.json()

        except requests.exceptions.Timeout:
            raise NetworkError("Request timeout", "Solcast")
        except requests.exceptions.RequestException as e:
            if isinstance(e, requests.exceptions.HTTPError):
                raise NetworkError(f"HTTP {response.status_code}: {str(e)}", "Solcast")
            raise NetworkError(f"Request failed: {str(e)}", "Solcast")

    def _get_header_int(self, response, header_name: str) -> Optional[int]:
        """
        Get an integer value from response headers.

        Args:
            response: requests.Response object
            header_name: Header name to extract

        Returns:
            Integer value or None if not found or not a valid integer
        """
        try:
            value = response.headers.get(header_name)
            if value:
                return int(value)
        except (ValueError, TypeError):
            pass
        return None

    def _log_rate_limit_info(self, response) -> None:
        """
        Extract and log rate limit information from Solcast API response headers.

        Solcast provides rate limit info via headers:
        - x-rate-limit-limit: Total calls allowed per day
        - x-rate-limit-remaining: Calls remaining today
        - x-rate-limit-reset: Unix timestamp when quota resets

        Args:
            response: requests.Response object
        """
        try:
            limit = response.headers.get("x-rate-limit-limit", "unknown")
            remaining = response.headers.get("x-rate-limit-remaining", "unknown")
            reset = response.headers.get("x-rate-limit-reset", "unknown")

            # Only log if we have at least some rate limit info
            if any(v != "unknown" for v in [limit, remaining, reset]):
                # Import logging at method level to avoid circular imports
                import logging

                # Use the main application logger to ensure output appears in logs
                logger = logging.getLogger("growatt-charger")

                remaining_int = int(remaining) if remaining != "unknown" else None
                limit_int = int(limit) if limit != "unknown" else None
                reset_int = int(reset) if reset != "unknown" else None

                # For Solcast free tier, the X-Rate-Limit-Remaining header returns a
                # very large number (appears to be an internal rate limit, not the
                # actual API quota) Instead, we calculate actual remaining based on
                # the KNOWN hobbyist tier limit (10/day) and track calls via the
                # usage tracker
                if remaining_int is not None and limit_int is None:
                    # Known Solcast hobbyist tier limit: 10 calls per 24-hour rolling window
                    # Calculate actual remaining from total calls made
                    known_limit = 10

                    # Get tracker to find actual calls made
                    tracker = get_global_tracker()
                    stats = tracker.usage_stats.get("solcast", {})
                    total_calls_made = stats.get("total_calls", 0)

                    # Calculate actual remaining
                    actual_remaining = known_limit - total_calls_made

                    # Only use calculated value if it makes sense (0-10 range)
                    if 0 <= actual_remaining <= known_limit:
                        remaining_int = actual_remaining
                        limit_int = known_limit
                    else:
                        # Fallback: trust the header if calculation doesn't make sense
                        limit_int = 10  # Assume hobbyist tier

                # Format reset time if available
                reset_time_str = ""
                if reset_int is not None:
                    reset_dt = datetime.fromtimestamp(reset_int)
                    reset_time_str = f" (resets at {reset_dt.strftime('%Y-%m-%d %H:%M:%S')})"

                # Log useful information
                if remaining_int is not None and limit_int is not None:
                    percent_used = ((limit_int - remaining_int) / limit_int) * 100
                    logger.info(
                        f"Solcast API quota: {remaining_int}/{limit_int} calls remaining "
                        f"({percent_used:.1f}% used){reset_time_str}"
                    )

                    # Warn if getting close to limit
                    if remaining_int <= 2:
                        logger.warning(
                            f"Solcast API quota critically low: only {remaining_int} "
                            "calls remaining! "
                            "Consider using an unmetered API key or waiting for "
                            f"quota reset.{reset_time_str}"
                        )
                    elif remaining_int <= 5:
                        logger.info(
                            f"Solcast API quota approaching limit: {remaining_int} "
                            f"calls remaining{reset_time_str}"
                        )
                else:
                    # Fallback format if we can't parse as integers
                    logger.info(
                        f"Solcast API rate limit - Limit: {limit}, "
                        f"Remaining: {remaining}, Reset: {reset}{reset_time_str}"
                    )
        except Exception as e:
            # Silently fail rate limit logging - don't let it break forecast fetching
            import logging

            logger = logging.getLogger(__name__)
            logger.debug(f"Could not parse Solcast rate limit headers: {str(e)}")

    def _check_quota_available(self, required_calls: int = 1, min_buffer: int = 1) -> bool:
        """
        Check if sufficient quota is available before making API calls.

        This prevents wasting calls when quota is exhausted or critically low.

        Args:
            required_calls: Number of API calls we want to make
            min_buffer: Minimum calls to keep in reserve (default 1 to avoid hitting limit)

        Returns:
            True if enough quota available, False if should skip (quota exhausted or too low)
        """
        quota_status = get_quota_status("solcast")

        remaining = quota_status.get("quota_remaining")

        # If we don't know the remaining quota, assume we can proceed (first call or no tracking)
        if remaining is None:
            return True

        # Check if we have enough quota
        needed = required_calls + min_buffer
        if remaining < needed:
            import logging

            logger = logging.getLogger("growatt-charger")

            status = quota_status.get("status", "UNKNOWN")
            logger.warning(
                f"Solcast quota check: insufficient quota to proceed. "
                f"Remaining: {remaining}, Need: {needed}, Status: {status}. "
                f"Skipping Solcast forecast. Will use fallback provider."
            )
            return False

        return True

    def get_forecast(self) -> Dict:
        """
        Get full forecast from Solcast.
        If multiple resource IDs configured, fetches and combines them.

        Checks quota before making requests to avoid wasting calls on rate-limited accounts.

        Returns:
            Raw forecast data from Solcast (combined if multiple resources)

        Raises:
            RateLimitError: If quota exhausted
            ForecastProviderError: If forecast cannot be retrieved
        """
        # Determine how many calls we need
        num_calls_needed = len(self.resource_ids) if self.resource_ids else 1

        # Check quota before proceeding
        # We need num_calls_needed + 1 buffer to avoid hitting the exact limit
        if not self._check_quota_available(required_calls=num_calls_needed, min_buffer=1):
            raise RateLimitError(
                f"Insufficient quota: need {num_calls_needed} call(s), quota exhausted", "Solcast"
            )

        if self.resource_ids:
            # If multiple resources, fetch each and combine
            if len(self.resource_ids) == 1:
                return self._get_resource_forecast(self.resource_ids[0])
            else:
                return self._get_combined_forecast()
        else:
            # Use world radiation endpoint (requires paid tier)
            endpoint = "world_pv_power/forecasts"
            params = {
                "latitude": self.latitude,
                "longitude": self.longitude,
                "capacity": self.capacity,
                "tilt": self.tilt,
                "azimuth": self.azimuth,
                "format": "json",
            }
            return self._make_request(endpoint, params)

    def _get_resource_forecast(self, resource_id: str) -> Dict:
        """Get forecast for a single resource."""
        endpoint = f"rooftop_sites/{resource_id}/forecasts"
        params = {"format": "json"}
        return self._make_request(endpoint, params)

    def _get_combined_forecast(self) -> Dict:
        """
        Fetch and combine forecasts from multiple resources (arrays).

        Returns:
            Combined forecast with summed pv_estimate values
        """
        all_forecasts = []

        # Fetch each resource
        for resource_id in self.resource_ids:
            forecast = self._get_resource_forecast(resource_id)
            all_forecasts.append(forecast.get("forecasts", []))

        if not all_forecasts:
            return {"forecasts": []}

        # Combine forecasts by period_end timestamp
        combined_by_time = {}

        for resource_forecasts in all_forecasts:
            for entry in resource_forecasts:
                period_end = entry["period_end"]
                pv_estimate = entry.get("pv_estimate", 0)

                if period_end in combined_by_time:
                    # Sum the estimates
                    combined_by_time[period_end]["pv_estimate"] += pv_estimate
                else:
                    # Create new entry
                    combined_by_time[period_end] = {
                        "period_end": period_end,
                        "pv_estimate": pv_estimate,
                        "period": entry.get("period", "PT30M"),
                    }

        # Convert back to list
        combined_forecasts = sorted(combined_by_time.values(), key=lambda x: x["period_end"])

        return {"forecasts": combined_forecasts}

    def get_forecast_for_date(self, target_date: datetime) -> float:
        """
        Get total forecast generation for a specific date in Wh.

        Args:
            target_date: Date to get forecast for

        Returns:
            Total forecasted generation in watt-hours
        """
        forecast_data = self.get_forecast()

        # Solcast returns 'forecasts' array with period_end times and pv_estimate
        forecasts = forecast_data.get("forecasts", [])

        # Format target date for comparison
        target_date_str = target_date.strftime("%Y-%m-%d")

        total_wh = 0
        for entry in forecasts:
            # Parse period_end: "2025-10-14T00:30:00.0000000Z"
            period_end = datetime.fromisoformat(entry["period_end"].replace("Z", "+00:00"))

            # Check if this period is on our target date
            if period_end.strftime("%Y-%m-%d") == target_date_str:
                # pv_estimate is in kW for the period (typically 30 min periods)
                pv_kw = entry.get("pv_estimate", 0)

                # Convert to Wh (assuming 30-minute periods)
                # kW * 0.5 hours = kWh, * 1000 = Wh
                wh = pv_kw * 0.5 * 1000
                total_wh += wh

        return total_wh

    def get_hourly_forecast_for_date(self, target_date: datetime) -> Dict[datetime, float]:
        """
        Get hourly forecast generation for a specific date.

        Args:
            target_date: Date to get forecast for

        Returns:
            Dictionary mapping datetime to watts for each hour
        """
        forecast_data = self.get_forecast()
        forecasts = forecast_data.get("forecasts", [])

        target_date_str = target_date.strftime("%Y-%m-%d")

        # Aggregate 30-min periods into hourly
        hourly_data = {}

        for entry in forecasts:
            period_end = datetime.fromisoformat(entry["period_end"].replace("Z", "+00:00"))

            if period_end.strftime("%Y-%m-%d") == target_date_str:
                # Round to hour
                hour_key = period_end.replace(minute=0, second=0, microsecond=0)

                # pv_estimate is in kW
                pv_kw = entry.get("pv_estimate", 0)
                pv_w = pv_kw * 1000  # Convert to watts

                # Average the 30-min periods within the hour
                if hour_key in hourly_data:
                    hourly_data[hour_key] = (hourly_data[hour_key] + pv_w) / 2
                else:
                    hourly_data[hour_key] = pv_w

        return hourly_data
