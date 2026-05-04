import json
from datetime import datetime

import requests


class ForecastSolarMultiArray:
    """Fetch solar forecasts for multiple array orientations from Forecast.Solar"""

    def __init__(self, latitude, longitude, api_key=None):
        """
        Initialize with location

        Args:
            latitude: Your location latitude
            longitude: Your location longitude
            api_key: Optional API key for paid plans (None for free public API)
        """
        self.latitude = latitude
        self.longitude = longitude
        self.api_key = api_key
        self.base_url = "https://api.forecast.solar"

    def get_multi_array_forecast(self, arrays):
        """
        Get forecast for multiple arrays in separate calls (free API method)

        Args:
            arrays: List of dicts with 'declination', 'azimuth', 'kwp' keys

        Returns:
            Combined forecast data
        """
        all_forecasts = []

        for idx, array in enumerate(arrays, 1):
            print(f"\nFetching forecast for Array {idx}:")
            print(f"  Orientation: {self._azimuth_to_direction(array['azimuth'])}")
            print(f"  Declination: {array['declination']}°")
            print(f"  Capacity: {array['kwp']} kWp")

            forecast = self._fetch_single_array(
                array["declination"], array["azimuth"], array["kwp"]
            )

            if forecast:
                all_forecasts.append(
                    {
                        "array_id": idx,
                        "azimuth": array["azimuth"],
                        "kwp": array["kwp"],
                        "forecast": forecast,
                    }
                )

        if all_forecasts:
            return self._combine_forecasts(all_forecasts)
        return None

    def get_single_call_forecast(self, arrays, api_key_required=True):
        """
        Get forecast for multiple arrays in ONE call (requires paid API)

        Args:
            arrays: List of dicts with 'declination', 'azimuth', 'kwp' keys
            api_key_required: Set False to try without key (will likely fail)

        Returns:
            Combined forecast data
        """
        if api_key_required and not self.api_key:
            raise ValueError("API key required for multi-array single call")

        # Build URL with all arrays
        # Format: /lat/lon/dec1/az1/kwp1/dec2/az2/kwp2/dec3/az3/kwp3
        array_params = []
        for array in arrays:
            array_params.extend(
                [str(array["declination"]), str(array["azimuth"]), str(array["kwp"])]
            )

        # Construct URL
        if self.api_key:
            url = (
                f"{self.base_url}/{self.api_key}/estimate/watthours/"
                f"{self.latitude}/{self.longitude}/"
                f"{'/'.join(array_params)}"
            )
        else:
            url = (
                f"{self.base_url}/estimate/watthours/"
                f"{self.latitude}/{self.longitude}/"
                f"{'/'.join(array_params)}"
            )

        print("\nFetching combined forecast...")
        print(f"URL: {url}")

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            print(f"HTTP Error: {e}")
            if e.response.status_code == 403:
                print("403 Forbidden - Multi-array queries require a paid API plan")
            return None
        except Exception as e:
            print(f"Error: {e}")
            return None

    @staticmethod
    def safe_int(value, default):
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def read_rate_limit(response, data, default_limit, default_remaining):
        limit_header = response.headers.get("X-Ratelimit-Limit")
        remain_header = response.headers.get("X-Ratelimit-Remaining")

        limit = ForecastSolarMultiArray.safe_int(limit_header, None)
        remaining = ForecastSolarMultiArray.safe_int(remain_header, None)

        if limit is None or remaining is None:
            print("  No rate limit info in response headers, checking body...")
            message = data.get("message", {})
            block = message.get("ratelimit", {})
            if limit is None:
                limit = ForecastSolarMultiArray.safe_int(block.get("limit"), default_limit)
            if remaining is None:
                remaining = ForecastSolarMultiArray.safe_int(
                    block.get("remaining"), default_remaining
                )

        return limit, remaining

    def _fetch_single_array(self, declination, azimuth, kwp):
        """Fetch forecast for a single array"""
        if self.api_key:
            url = (
                f"{self.base_url}/{self.api_key}/estimate/watthours/"
                f"{self.latitude}/{self.longitude}/"
                f"{declination}/{azimuth}/{kwp}"
            )
        else:
            url = (
                f"{self.base_url}/estimate/watthours/"
                f"{self.latitude}/{self.longitude}/"
                f"{declination}/{azimuth}/{kwp}"
            )

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            # # Check rate limit info
            # if "X-Ratelimit-Limit" in response.headers:
            #     rate_limit = int(response.headers.get("X-Ratelimit-Limit", 12))
            #     rate_remaining = int(response.headers.get("X-Ratelimit-Remaining", 0))
            #     print(f"  Rate limit: {rate_remaining}/{rate_limit}")
            # else:
            #     print("  No rate limit info in response headers")

            rate_limit, rate_remaining = ForecastSolarMultiArray.read_rate_limit(
                response, data, default_limit=12, default_remaining=0
            )

            print(f" Rate limit: {rate_remaining}/{rate_limit}")

            print(f"  Forecast fetched successfully: {data}")
            return data
        except requests.exceptions.HTTPError as e:
            print(f"  HTTP Error: {e}")
            return None
        except Exception as e:
            print(f"  Error: {e}")
            return None

    def _combine_forecasts(self, forecasts):
        """Combine multiple array forecasts into totals"""
        if not forecasts:
            return None

        combined = {
            "arrays": forecasts,
            "combined_wh": {},
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "total_capacity_kwp": sum(f["kwp"] for f in forecasts),
            },
        }

        # Get all unique timestamps from all arrays
        all_timestamps = set()
        for f in forecasts:
            if "result" in f["forecast"]:
                # The result is a flat dict of timestamp: watt-hours
                all_timestamps.update(f["forecast"]["result"].keys())

        # Sum cumulative watt-hours for each timestamp
        for timestamp in sorted(all_timestamps):
            total_wh = 0

            for f in forecasts:
                if "result" in f["forecast"]:
                    result = f["forecast"]["result"]
                    # Result is directly timestamp: watt-hours (cumulative)
                    total_wh += result.get(timestamp, 0)

            combined["combined_wh"][timestamp] = total_wh

        return combined

    def _azimuth_to_direction(self, azimuth):
        """
        Convert azimuth to compass direction.

        Forecast.Solar uses: -180=North, -90=East, 0=South, 90=West, 180=North
        """
        # Map azimuth values to directions
        if azimuth == -180 or azimuth == 180:
            return "North"
        elif azimuth == -90:
            return "East"
        elif azimuth == 0:
            return "South"
        elif azimuth == 90:
            return "West"
        elif -180 < azimuth < -90:
            return "NE"
        elif -90 < azimuth < 0:
            return "SE"
        elif 0 < azimuth < 90:
            return "SW"
        elif 90 < azimuth < 180:
            return "NW"
        else:
            return f"{azimuth}°"

    def print_summary(self, forecast_data, hours=24):
        """Print a summary of the forecast"""
        if not forecast_data:
            print("No forecast data available")
            return

        print("\n" + "=" * 60)
        print("FORECAST SUMMARY")
        print("=" * 60)

        # Print array info
        total_kwp = forecast_data["metadata"]["total_capacity_kwp"]
        print(f"\nTotal System Capacity: {total_kwp:.2f} kWp")
        print(f"Number of Arrays: {len(forecast_data['arrays'])}")

        for array in forecast_data["arrays"]:
            print(f"\nArray {array['array_id']}:")
            direction = self._azimuth_to_direction(array["azimuth"])
            print(f"  Direction: {direction} ({array['azimuth']}°)")
            print(f"  Capacity: {array['kwp']} kWp")

        # Calculate tomorrow's totals (extract date-based totals)
        self._print_daily_totals(forecast_data)

        # Print hourly forecast for next N hours
        print(f"\n{'=' * 60}")
        print(f"HOURLY FORECAST - NEXT {hours} HOURS")
        print(f"{'=' * 60}")
        print(f"{'Time':<20} {'Cumulative (Wh)':<15}")
        print("-" * 60)

        timestamps = sorted(list(forecast_data["combined_wh"].keys()))[:hours]
        for ts in timestamps:
            wh = forecast_data["combined_wh"][ts]
            print(f"{ts:<20} {wh:<15.0f}")

        # Total energy (max cumulative value)
        if forecast_data["combined_wh"]:
            total_energy = max(forecast_data["combined_wh"].values()) / 1000
            print("-" * 60)
            print(f"Total forecasted energy: {total_energy:.2f} kWh")

    def _print_daily_totals(self, forecast_data):
        """Print daily energy totals per array and combined"""
        print(f"\n{'=' * 60}")
        print("DAILY ENERGY FORECAST")
        print(f"{'=' * 60}")

        # Group by date
        daily_totals = {}
        daily_array_totals = {}

        # Process combined totals (cumulative wh per timestamp, get max per day)
        for timestamp, wh in forecast_data["combined_wh"].items():
            date = timestamp.split()[0]
            if date not in daily_totals:
                daily_totals[date] = 0
            # Watt-hours are cumulative for the day, so take the max value
            daily_totals[date] = max(daily_totals[date], wh)

        # Process per-array totals
        for array in forecast_data["arrays"]:
            array_id = array["array_id"]
            if "result" in array["forecast"]:
                # Result is flat dict of timestamp: cumulative watt-hours
                for timestamp, wh in array["forecast"]["result"].items():
                    date = timestamp.split()[0]
                    if date not in daily_array_totals:
                        daily_array_totals[date] = {}
                    if array_id not in daily_array_totals[date]:
                        daily_array_totals[date][array_id] = 0
                    # Take max cumulative value for the day
                    daily_array_totals[date][array_id] = max(daily_array_totals[date][array_id], wh)

        # Print daily breakdown
        for date in sorted(daily_totals.keys()):
            print(f"\n{date}:")

            # Per-array breakdown
            if date in daily_array_totals:
                for array in forecast_data["arrays"]:
                    array_id = array["array_id"]
                    direction = self._azimuth_to_direction(array["azimuth"])
                    kwh = daily_array_totals[date].get(array_id, 0) / 1000
                    print(f"  Array {array_id} ({direction:5s}): {kwh:6.2f} kWh")

            # Total for the day
            total_kwh = daily_totals[date] / 1000
            print(f"  {'─' * 25}")
            print(f"  {'TOTAL':12s}: {total_kwh:6.2f} kWh")


# Example usage
if __name__ == "__main__":
    # Your location (Colchester area)
    LAT = 51.913599
    LON = 0.855471

    # Define your arrays
    # Based on your actual system: 5.8 kWp / 15 panels = ~387W per panel
    PANEL_WATTS = 0.387  # 387W panels (5.8kWp ÷ 15 panels)
    TILT = 35  # degrees (your roof pitch)

    # Forecast.Solar azimuth convention:
    # -180 = North, -90 = East, 0 = South, 90 = West, 180 = North
    arrays = [
        {
            "name": "East Array",
            "declination": TILT,
            "azimuth": -90,  # East
            "kwp": 6 * PANEL_WATTS,  # 2.32 kWp (6 panels)
        }  # ,
        # {
        #     "name": "South Array",
        #     "declination": TILT,
        #     "azimuth": 0,  # South
        #     "kwp": 3 * PANEL_WATTS,  # 1.16 kWp (3 panels)
        # },
        # {
        #     "name": "West Array",
        #     "declination": TILT,
        #     "azimuth": 90,  # West
        #     "kwp": 6 * PANEL_WATTS,  # 2.32 kWp (6 panels)
        # },
    ]

    # Initialize forecaster (no API key = free public API)
    forecaster = ForecastSolarMultiArray(LAT, LON, api_key=None)

    print("=" * 60)
    print("FORECAST.SOLAR MULTI-ARRAY FETCHER")
    print("=" * 60)
    print(f"Location: {LAT}, {LON}")
    print(f"Total System: {sum(a['kwp'] for a in arrays):.2f} kWp")
    print(f"Arrays: {len(arrays)}")

    # Fetch forecasts (separate calls for free API)
    forecast = forecaster.get_multi_array_forecast(arrays)

    if forecast:
        forecaster.print_summary(forecast, hours=48)

        # Optionally save to file
        with open("solar_forecast.json", "w") as f:
            json.dump(forecast, f, indent=2)
        print("\nForecast saved to solar_forecast.json")
    else:
        print("\nFailed to fetch forecast")
