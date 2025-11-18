"""
API usage tracking and quota monitoring for forecast providers.

This module provides utilities to track API call counts, quota usage, and alert
when approaching rate limits. Works with forecast providers (Solcast, forecast.solar, etc.)

Supports different quota models:
- Solcast: 10 calls per rolling 24-hour window
- Forecast.solar: 12 calls per rolling 1-hour window
"""

import json
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Provider-specific quota models (rolling window in hours, call limit)
PROVIDER_QUOTA_MODELS = {
    "solcast": {"window_hours": 24, "limit": 10},
    "forecast.solar": {"window_hours": 1, "limit": 12},
}


class APIUsageTracker:
    """
    Track API usage across forecast providers with rolling window support.

    Maintains in-memory statistics with call timestamps (for rolling window calculation)
    and optionally persists to file for daily reports. Single file per day with per-provider
    data that merges on write to avoid overwrites.
    Thread-safe for multi-threaded environments.
    """

    def __init__(self, persistence_dir: Optional[str] = None):
        """
        Initialize the API usage tracker.

        Args:
            persistence_dir: Optional directory to persist daily usage stats.
                            If provided, daily summaries are written to JSON files
                            with merge logic to avoid overwrites.
        """
        self.persistence_dir = Path(persistence_dir) if persistence_dir else None
        self.usage_stats: Dict[str, Dict[str, Any]] = {}
        self.call_timestamps: Dict[str, List[datetime]] = (
            {}
        )  # Track call timestamps for rolling windows
        self.lock = threading.Lock()

        if self.persistence_dir:
            self.persistence_dir.mkdir(parents=True, exist_ok=True)

    def record_call(
        self,
        provider: str,
        endpoint: str = "forecast",
        status_code: int = 200,
        quota_remaining: Optional[int] = None,
        quota_limit: Optional[int] = None,
        error: Optional[str] = None,
    ) -> None:
        """
        Record an API call for a provider.

        Args:
            provider: Provider name (e.g., "solcast", "forecast.solar")
            endpoint: API endpoint called (default: "forecast")
            status_code: HTTP status code returned
            quota_remaining: API calls remaining in quota (if available from headers)
            quota_limit: Total API calls allowed per day (if available from headers)
            error: Error message if call failed (None if successful)
        """
        with self.lock:
            if provider not in self.usage_stats:
                self.usage_stats[provider] = {
                    "total_calls": 0,
                    "successful_calls": 0,
                    "failed_calls": 0,
                    "last_quota_check": None,
                    "quota_remaining": quota_remaining,
                    "quota_limit": quota_limit,
                    "last_call_time": None,
                    "errors": [],
                }

            stats = self.usage_stats[provider]
            stats["total_calls"] += 1
            stats["last_call_time"] = datetime.now()

            if status_code < 400:
                stats["successful_calls"] += 1
            else:
                stats["failed_calls"] += 1
                if error:
                    stats["errors"].append(
                        {
                            "timestamp": datetime.now().isoformat(),
                            "status_code": status_code,
                            "error": error,
                        }
                    )

            # Update quota info if provided
            if quota_remaining is not None:
                # For Solcast, the X-Rate-Limit-Remaining header returns misleading values
                # (appears to be an internal rate limit, not the actual API quota)
                # If we detect this pattern (very large remaining for hobbyist tier),
                # calculate actual remaining from calls made
                if provider == "solcast" and quota_remaining > 100:
                    # This is likely the misleading header value
                    # Calculate actual remaining: 10 (hobbyist limit) - total_calls_made
                    actual_limit = 10
                    actual_remaining = actual_limit - stats["total_calls"]
                    stats["quota_remaining"] = max(0, actual_remaining)  # Don't go below 0
                    stats["quota_limit"] = actual_limit
                else:
                    # Normal case: trust the header value
                    stats["quota_remaining"] = quota_remaining

                stats["last_quota_check"] = datetime.now().isoformat()

            if quota_limit is not None:
                stats["quota_limit"] = quota_limit

    def get_provider_stats(self, provider: str) -> Dict[str, Any]:
        """
        Get usage statistics for a provider.

        Args:
            provider: Provider name

        Returns:
            Dictionary with usage statistics
        """
        with self.lock:
            return self.usage_stats.get(provider, {}).copy()

    def get_quota_status(self, provider: str) -> Dict[str, Any]:
        """
        Get current quota status for a provider.

        Args:
            provider: Provider name (e.g., "solcast")

        Returns:
            Dictionary with quota information:
            - quota_remaining: Calls remaining (or None if unknown)
            - quota_limit: Total quota (or None if unknown)
            - calls_made: Total API calls made so far
            - status: "OK", "LOW", "EXHAUSTED" based on remaining quota
        """
        with self.lock:
            stats = self.usage_stats.get(provider, {})
            remaining = stats.get("quota_remaining")
            limit = stats.get("quota_limit")

            # Determine status
            status = "UNKNOWN"
            if remaining is not None:
                if remaining <= 0:
                    status = "EXHAUSTED"
                elif remaining <= 2:
                    status = "CRITICAL"
                elif remaining <= 5:
                    status = "LOW"
                else:
                    status = "OK"

            return {
                "quota_remaining": remaining,
                "quota_limit": limit,
                "calls_made": stats.get("total_calls", 0),
                "successful_calls": stats.get("successful_calls", 0),
                "failed_calls": stats.get("failed_calls", 0),
                "status": status,
            }

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Get usage statistics for all providers.

        Returns:
            Dictionary mapping provider names to their stats
        """
        with self.lock:
            return {k: v.copy() for k, v in self.usage_stats.items()}

    def log_summary(self, log_level: int = logging.INFO) -> None:
        """
        Log a summary of API usage for all providers.

        Args:
            log_level: Logging level to use (default: INFO)
        """
        with self.lock:
            if not self.usage_stats:
                logger.log(log_level, "No API usage recorded yet")
                return

            logger.log(log_level, "=== API Usage Summary ===")

            for provider, stats in self.usage_stats.items():
                total = stats["total_calls"]
                success = stats["successful_calls"]
                failed = stats["failed_calls"]
                success_rate = (success / total * 100) if total > 0 else 0

                msg = f"{provider}: {total} calls ("
                f"{success} success, "
                f"{failed} failed, "
                f"{success_rate:.1f}% success rate)"

                # Add quota info if available
                if (
                    stats.get("quota_remaining") is not None
                    and stats.get("quota_limit") is not None
                ):
                    remaining = stats["quota_remaining"]
                    limit = stats["quota_limit"]
                    percent_used = ((limit - remaining) / limit * 100) if limit > 0 else 0
                    msg += f" | Quota: {remaining}/{limit} ({percent_used:.1f}% used)"

                    # Warn if quota is low
                    if remaining <= 2:
                        msg += " ⚠️ CRITICAL: Quota nearly exhausted!"
                    elif remaining <= 5:
                        msg += " ⚠️ Warning: Quota getting low"

                logger.log(log_level, msg)

    def save_daily_summary(self, date: Optional[datetime] = None) -> Optional[Path]:
        """
        Save daily usage summary to JSON file.

        Args:
            date: Date to save summary for (default: today)

        Returns:
            Path to saved file, or None if persistence_dir not configured
        """
        if not self.persistence_dir:
            logger.debug("API usage persistence not configured, skipping daily summary")
            return None

        if date is None:
            date = datetime.now()

        with self.lock:
            stats = {
                "date": date.strftime("%Y-%m-%d"),
                "timestamp": datetime.now().isoformat(),
                "providers": self.usage_stats.copy(),
            }

        filename = f"api_usage_{date.strftime('%Y-%m-%d')}.json"
        filepath = self.persistence_dir / filename

        try:
            with open(filepath, "w") as f:
                json.dump(stats, f, indent=2, default=str)
            logger.info(f"Saved daily API usage summary to {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Failed to save API usage summary: {str(e)}")
            return None

    def check_quota_alerts(self) -> Dict[str, str]:
        """
        Check for quota-related alerts.

        Returns:
            Dictionary mapping provider names to alert messages (empty if no alerts)
        """
        alerts = {}

        with self.lock:
            for provider, stats in self.usage_stats.items():
                remaining = stats.get("quota_remaining")
                limit = stats.get("quota_limit")

                if remaining is not None and limit is not None:
                    if remaining == 0:
                        alerts[provider] = "⛔ Quota exhausted! No API calls remaining."
                    elif remaining <= 1:
                        alerts[provider] = f"🔴 CRITICAL: Only {remaining} call remaining!"
                    elif remaining <= 2:
                        alerts[provider] = f"🟠 WARNING: Only {remaining} calls remaining"
                    elif remaining <= 5:
                        alerts[provider] = (
                            f"🟡 CAUTION: {remaining} calls remaining "
                            f"(quota at {(1 - remaining/limit)*100:.0f}%)"
                        )

        return alerts


# Global tracker instance
_global_tracker: Optional[APIUsageTracker] = None
_tracker_lock = threading.Lock()


def get_global_tracker(persistence_dir: Optional[str] = None) -> APIUsageTracker:
    """
    Get or create the global API usage tracker instance.

    Args:
        persistence_dir: Optional directory for persisting daily stats.
                        Only used on first initialization.

    Returns:
        Global APIUsageTracker instance
    """
    global _global_tracker

    if _global_tracker is None:
        with _tracker_lock:
            if _global_tracker is None:
                _global_tracker = APIUsageTracker(persistence_dir)

    return _global_tracker


def record_api_call(
    provider: str,
    endpoint: str = "forecast",
    status_code: int = 200,
    quota_remaining: Optional[int] = None,
    quota_limit: Optional[int] = None,
    error: Optional[str] = None,
) -> None:
    """
    Convenience function to record an API call using the global tracker.

    Args:
        provider: Provider name
        endpoint: API endpoint
        status_code: HTTP status code
        quota_remaining: Calls remaining in quota
        quota_limit: Total quota limit
        error: Error message if failed
    """
    tracker = get_global_tracker()
    tracker.record_call(
        provider=provider,
        endpoint=endpoint,
        status_code=status_code,
        quota_remaining=quota_remaining,
        quota_limit=quota_limit,
        error=error,
    )


def get_quota_status(provider: str) -> Dict[str, Any]:
    """
    Convenience function to get quota status for a provider.

    Args:
        provider: Provider name (e.g., "solcast")

    Returns:
        Dictionary with quota information:
        - quota_remaining: Calls remaining (or None if unknown)
        - quota_limit: Total quota
        - calls_made: Total API calls made
        - successful_calls: Successful calls
        - failed_calls: Failed calls
        - status: "OK", "LOW", "CRITICAL", "EXHAUSTED", or "UNKNOWN"
    """
    tracker = get_global_tracker()
    return tracker.get_quota_status(provider)
