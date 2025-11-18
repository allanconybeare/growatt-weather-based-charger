import json
from datetime import datetime

import requests

# Configuration
API_KEY = "HynmFM4W1PPP7PbJras4lOOvqpCSJZWH"  # Replace with your actual API key
BASE_URL = "https://api.solcast.com.au"

# Example endpoint - replace with the one you're using
# - /rooftop_sites/{resource_id}/forecasts
# RESOURCE_IDS = "d367-4a1c-0d79-32b9" #, cc26-bafb-3efe-7573"

RESOURCE_IDS = [
    "d367-4a1c-0d79-32b9"  # ,
    # "cc26-bafb-3efe-7573" # can uncomment to test multiple arrays
]

# Example parameters - adjust based on your needs
params = {"format": "json"}


def test_api_call():
    """Test the Solcast API and display detailed response information"""

    print("=" * 60)
    print("SOLCAST API RATE LIMIT DIAGNOSTIC TEST")
    print(f"Testing {len(RESOURCE_IDS)} rooftop site(s)")
    print("=" * 60)
    print(f"\nTest Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API Key (first 10 chars): {API_KEY[:10]}...")
    print("\n" + "-" * 60)

    all_forecasts = []

    for idx, resource_id in enumerate(RESOURCE_IDS, 1):
        endpoint = f"/rooftop_sites/{resource_id}/forecasts"

        print(f"\n{'=' * 60}")
        print(f"SITE {idx} of {len(RESOURCE_IDS)}: {resource_id}")
        print(f"{'=' * 60}")
        print(f"Endpoint: {BASE_URL}{endpoint}")

        try:
            # Make the API request
            headers = {"Authorization": f"Bearer {API_KEY}"}

            print("\nMaking API request...")
            response = requests.get(
                f"{BASE_URL}{endpoint}", headers=headers, params=params, timeout=10
            )

            # Display status code
            print(f"\n✓ Response Status Code: {response.status_code}")

            # Display key response headers
            print("\n" + "-" * 60)
            print("KEY HEADERS:")
            print("-" * 60)
            key_headers = ["X-Rate-Limit", "X-Rate-Limit-Remaining", "X-Rate-Limit-Reset"]
            for header in key_headers:
                if header in response.headers:
                    print(f"{header}: {response.headers[header]}")
                    if "reset" in header.lower():
                        try:
                            reset_timestamp = int(response.headers[header])
                            reset_time = datetime.fromtimestamp(reset_timestamp)
                            print(f"  → Reset Time: {reset_time.strftime('%Y-%m-%d %H:%M:%S')}")
                        except (FileNotFoundError, KeyError, ValueError, AttributeError) as e:
                            print(f"Conscious decision to ignore this: {e}")
                            pass

            # Display response body summary
            print("\n" + "-" * 60)
            print("RESPONSE SUMMARY:")
            print("-" * 60)

            if response.status_code == 200:
                try:
                    json_response = response.json()

                    # Store forecast data
                    all_forecasts.append({"resource_id": resource_id, "data": json_response})

                    # Show summary of forecast data
                    if "forecasts" in json_response:
                        forecast_count = len(json_response["forecasts"])
                        print(f"✓ SUCCESS: Received {forecast_count} forecast periods")

                        # Show first forecast entry as example
                        if forecast_count > 0:
                            first = json_response["forecasts"][0]
                            print("\nFirst forecast period:")
                            print(f"  Period End: {first.get('period_end', 'N/A')}")
                            print(f"  PV Estimate: {first.get('pv_estimate', 'N/A')} kW")
                            if "pv_estimate10" in first:
                                print(
                                    f"  PV Estimate (10th percentile): {first['pv_estimate10']} kW"
                                )
                                print(
                                    f"  PV Estimate (90th percentile): {first['pv_estimate90']} kW"
                                )
                    else:
                        print(json.dumps(json_response, indent=2))

                except Exception as e:
                    print(f"✗ Error parsing response: {e}")
                    print(response.text)
            else:
                # Show error response
                try:
                    json_response = response.json()
                    print(json.dumps(json_response, indent=2))
                except (FileNotFoundError, KeyError, ValueError, AttributeError) as e:
                    # Log the error if you have logging set up
                    print(f"Warning: {e}")
                    print(response.text)

                # Interpretation
                if response.status_code == 429:
                    print("\n✗ RATE LIMITED: You've exceeded your API quota")
                elif response.status_code == 401:
                    print("\n✗ UNAUTHORIZED: Invalid or expired API key")
                elif response.status_code == 403:
                    print("\n✗ FORBIDDEN: Endpoint not available for your account tier")
                elif response.status_code == 404:
                    print("\n✗ NOT FOUND: Rooftop site doesn't exist or isn't accessible")
                else:
                    print(f"\n✗ ERROR: Received status code {response.status_code}")

        except requests.exceptions.Timeout:
            print("\n✗ ERROR: Request timed out")
        except requests.exceptions.ConnectionError:
            print("\n✗ ERROR: Connection failed")
        except Exception as e:
            print(f"\n✗ ERROR: {type(e).__name__}: {str(e)}")

    # Summary of all sites
    if all_forecasts:
        print("\n" + "=" * 60)
        print("COMBINED FORECAST SUMMARY")
        print("=" * 60)

        # Calculate combined power for first forecast period
        if all(f["data"].get("forecasts") for f in all_forecasts):
            first_periods = [f["data"]["forecasts"][0] for f in all_forecasts]
            total_pv = sum(p.get("pv_estimate", 0) for p in first_periods)

            print("\nTotal system capacity (first period):")
            print(f"  Combined PV Estimate: {total_pv:.2f} kW")
            print("\nBreakdown by array:")
            for i, forecast in enumerate(all_forecasts, 1):
                pv_val = forecast["data"]["forecasts"][0].get("pv_estimate", 0)
                print(f"  Array {i} ({forecast['resource_id']}): {pv_val:.2f} kW")

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)


def dry_run():
    """Show what will be called without making the actual request"""
    print("=" * 60)
    print("DRY RUN - NO API CALL WILL BE MADE")
    print("=" * 60)
    print(f"\nAPI Key: {API_KEY[:10]}...{API_KEY[-4:]}")
    print(f"Testing {len(RESOURCE_IDS)} rooftop site(s)")

    for idx, resource_id in enumerate(RESOURCE_IDS, 1):
        endpoint = f"/rooftop_sites/{resource_id}/forecasts"
        print(f"\n--- Site {idx} ---")
        print(f"Full URL: {BASE_URL}{endpoint}")
        print(f"Parameters: {json.dumps(params, indent=2)}")
        param_str = "&".join([f"{k}={v}" for k, v in params.items()])
        print(f"Full request URL: {BASE_URL}{endpoint}?{param_str}")

    print(f"\nNote: This will use {len(RESOURCE_IDS)} of your daily API calls")
    print("=" * 60)


if __name__ == "__main__":
    # Check if API key is set
    if API_KEY == "YOUR_API_KEY_HERE":
        print("ERROR: Please set your API_KEY in the script!")
        print("Edit the script and replace 'YOUR_API_KEY_HERE' with your actual Solcast API key")
    elif not RESOURCE_IDS or RESOURCE_IDS[0] == "YOUR_RESOURCE_ID_HERE":
        print("ERROR: Please set your RESOURCE_IDS in the script!")
        print("Get your resource IDs from: https://toolkit.solcast.com.au/rooftop-sites")
    else:
        # Comment the next line to do an actual call to the API will use one of your calls
        dry_run()

        # Uncomment out this line if doing an actual test
        # test_api_call()

        # Option to test multiple times
        print("\nRun this script again to perform another test.")
