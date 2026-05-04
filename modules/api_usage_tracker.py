"""
Enhanced API usage tracking with rolling window support and per-provider persistence.

Key improvements:
- Separate JSON file per provider (no overwrites)
- Rolling window calculations (24h for Solcast, 1h for Forecast.Solar)
- Timestamp tracking for all calls
- Proper handling of Solcast's misleading headers
- Thread-safe operations
"""

import json
import logging
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

# logger = logging.getLogger(__name__)

# Provider-specific quota models
PROVIDER_QUOTA_MODELS = {
    "solcast": {
        "window_hours": 24,  # Rolling 24-hour window
        "limit": 10,  # Hobbyist tier: 10 calls per 24h
        "reset_type": "rolling",  # Resets 24h from each call
    },
    "forecast.solar": {
        "window_hours": 1,  # Rolling 1-hour window
        "limit": 12,  # Free tier: 12 calls per hour
        "reset_type": "fixed",  # Resets at top of each hour
    },
}


class APIUsageTracker:
    """
    Track API usage with rolling window support and per-provider persistence.

    Each provider gets its own JSON file to avoid overwrites.
    Maintains call timestamps for accurate rolling window calculations.
    """

    def __init__(self, persistence_dir: Optional[str] = None):
        """
        Initialize the API usage tracker.

        Args:
            persistence_dir: Directory to persist usage data (one file per provider)
        """
        # Add instance logger
        self.logger = logging.getLogger(__name__)

        self.persistence_dir = Path(persistence_dir) if persistence_dir else None
        self.lock = threading.Lock()

        # In-memory storage: provider -> list of call records
        self.call_history: Dict[str, List[Dict[str, Any]]] = {}

        if self.persistence_dir:
            self.persistence_dir.mkdir(parents=True, exist_ok=True)
            self._load_all_providers()

    def _get_provider_file(self, provider: str) -> Path:
        """Get the persistence file path for a provider."""
        return self.persistence_dir / f"api_usage_{provider}.json"

    def _load_all_providers(self) -> None:
        """Load existing usage data for all providers on startup."""
        if not self.persistence_dir:
            return

        # Look for all api_usage_*.json files
        for filepath in self.persistence_dir.glob("api_usage_*.json"):
            provider = filepath.stem.replace("api_usage_", "")
            try:
                with open(filepath, "r") as f:
                    data = json.load(f)
                    self.call_history[provider] = data.get("call_history", [])
                    self.logger.info(
                        f"Loaded {len(self.call_history[provider])} calls for {provider}"
                    )
            except Exception as e:
                self.logger.warning(f"Could not load usage data for {provider}: {e}")
                self.call_history[provider] = []

    def _save_provider(self, provider: str) -> None:
        """Save usage data for a specific provider."""
        if not self.persistence_dir:
            return

        filepath = self._get_provider_file(provider)

        try:
            data = {
                "provider": provider,
                "last_updated": datetime.now().isoformat(),
                "quota_model": PROVIDER_QUOTA_MODELS.get(provider, {}),
                "call_history": self.call_history.get(provider, []),
            }

            with open(filepath, "w") as f:
                json.dump(data, f, indent=2, default=str)

        except Exception as e:
            self.logger.error(f"Failed to save usage data for {provider}: {e}")

    def _cleanup_old_calls(self, provider: str) -> None:
        """
        Remove calls outside the rolling window to keep file size manageable.

        For Solcast: keep 25 hours of history (24h window + 1h buffer)
        For Forecast.Solar: keep 2 hours of history (1h window + 1h buffer)
        """
        if provider not in self.call_history:
            return

        quota_model = PROVIDER_QUOTA_MODELS.get(provider)
        if not quota_model:
            return

        # Calculate cutoff time
        window_hours = quota_model["window_hours"]
        buffer_hours = 1  # Keep extra hour as buffer

        # For fixed-window providers (Forecast.Solar), we need MORE buffer
        # because calls from the previous hour are still relevant until the top of the current hour
        if quota_model.get("reset_type") == "fixed":
            # Keep 2 full hours of history to handle hour boundaries properly
            buffer_hours = window_hours + 1  # So 1h window + 1h = 2h total

        cutoff = datetime.now() - timedelta(hours=window_hours + buffer_hours)

        # Filter out old calls
        original_count = len(self.call_history[provider])
        self.call_history[provider] = [
            call
            for call in self.call_history[provider]
            if datetime.fromisoformat(call["timestamp"]) > cutoff
        ]

        removed = original_count - len(self.call_history[provider])
        if removed > 0:
            self.logger.debug(f"Cleaned up {removed} old calls for {provider}")

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
            endpoint: API endpoint called
            status_code: HTTP status code
            quota_remaining: Reported quota remaining (may be inaccurate for Solcast)
            quota_limit: Reported quota limit
            error: Error message if call failed
        """
        with self.lock:
            if provider not in self.call_history:
                self.call_history[provider] = []

            # Create call record with timestamp
            call_record = {
                "timestamp": datetime.now().isoformat(),
                "endpoint": endpoint,
                "status_code": status_code,
                "success": status_code < 400,
                "error": error,
            }

            # Only trust quota info from headers for specific providers
            # For Solcast, we'll calculate it ourselves due to misleading headers
            if provider == "solcast":
                # Don't trust Solcast's X-Rate-Limit-Remaining (counts down from 600)
                # We'll calculate based on our own call tracking
                call_record["reported_remaining"] = quota_remaining
                call_record["reported_limit"] = quota_limit
            else:
                # For Forecast.Solar and others, trust the headers
                call_record["quota_remaining"] = quota_remaining
                call_record["quota_limit"] = quota_limit

            # Add to history
            self.call_history[provider].append(call_record)

            # Log the call
            status = "SUCCESS" if call_record["success"] else "FAILED"
            self.logger.info(
                f"API call recorded: {provider} - {endpoint} - {status} " f"(HTTP {status_code})"
            )

            # Cleanup old calls to keep file size reasonable
            self._cleanup_old_calls(provider)

            # Save immediately after each call
            self._save_provider(provider)

    def _get_calls_in_window_unlocked(self, provider: str) -> List[Dict[str, Any]]:
        """
        Get all calls within the provider's rolling window (internal, no locking).

        Args:
            provider: Provider name

        Returns:
            List of call records within the rolling window
        """
        if provider not in self.call_history:
            return []

        quota_model = PROVIDER_QUOTA_MODELS.get(provider)
        if not quota_model:
            # Unknown provider, return all calls
            return self.call_history[provider]

        # Calculate window start time
        window_hours = quota_model["window_hours"]
        window_start = datetime.now() - timedelta(hours=window_hours)

        # Filter calls within window
        calls_in_window = [
            call
            for call in self.call_history[provider]
            if datetime.fromisoformat(call["timestamp"]) > window_start
        ]

        return calls_in_window

    def get_calls_in_window(self, provider: str) -> List[Dict[str, Any]]:
        """
        Get all calls within the provider's rolling window.

        Args:
            provider: Provider name

        Returns:
            List of call records within the rolling window
        """
        with self.lock:
            return self._get_calls_in_window_unlocked(provider)

    def _get_quota_status_unlocked(self, provider: str) -> Dict[str, Any]:
        """
        Get quota status (internal, no locking).

        Args:
            provider: Provider name

        Returns:
            Dictionary with quota status
        """
        quota_model = PROVIDER_QUOTA_MODELS.get(provider, {})
        limit = quota_model.get("limit", 0)
        window_hours = quota_model.get("window_hours", 24)

        # Get calls in current window (use internal unlocked version)
        calls = self._get_calls_in_window_unlocked(provider)
        calls_in_window = len(calls)

        # Calculate remaining
        remaining = max(0, limit - calls_in_window)

        # Calculate reset time (for rolling windows)
        reset_time = None
        if calls and quota_model.get("reset_type") == "rolling":
            # For rolling windows, quota resets when oldest call expires
            oldest_call = min(calls, key=lambda c: c["timestamp"])
            oldest_time = datetime.fromisoformat(oldest_call["timestamp"])
            reset_time = oldest_time + timedelta(hours=window_hours)
        elif quota_model.get("reset_type") == "fixed":
            # For fixed windows (hourly), quota resets at top of next hour
            now = datetime.now()
            reset_time = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)

        # Determine status
        if remaining <= 0:
            status = "EXHAUSTED"
        elif remaining <= 2:
            status = "CRITICAL"
        elif remaining <= 5:
            status = "LOW"
        else:
            status = "OK"

        # Get success/failure counts
        successful = sum(1 for c in calls if c.get("success", False))
        failed = len(calls) - successful

        return {
            "provider": provider,
            "calls_in_window": calls_in_window,
            "successful_calls": successful,
            "failed_calls": failed,
            "quota_limit": limit,
            "quota_remaining": remaining,
            "quota_used_pct": (calls_in_window / limit * 100) if limit > 0 else 0,
            "window_hours": window_hours,
            "reset_time": reset_time.isoformat() if reset_time else None,
            "status": status,
        }

    def get_quota_status(self, provider: str) -> Dict[str, Any]:
        """
        Get current quota status for a provider with rolling window calculation.

        Args:
            provider: Provider name

        Returns:
            Dictionary with:
            - calls_in_window: Number of calls in the rolling window
            - quota_limit: Maximum calls allowed
            - quota_remaining: Calculated remaining calls
            - window_hours: Rolling window duration
            - reset_time: When quota resets (for rolling windows)
            - status: OK, LOW, CRITICAL, EXHAUSTED
        """
        with self.lock:
            return self._get_quota_status_unlocked(provider)

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Get quota status for all providers.

        Returns:
            Dictionary mapping provider names to their quota status
        """
        with self.lock:
            return {
                provider: self.get_quota_status(provider) for provider in self.call_history.keys()
            }

    def log_summary(self, log_level: int = logging.INFO) -> None:
        """
        Log a summary of API usage for all providers.

        Args:
            log_level: Logging level to use
        """
        with self.lock:
            if not self.call_history:
                self.logger.log(log_level, "No API usage recorded yet")
                return

            self.logger.log(log_level, "=== API Usage Summary ===")

            for provider in self.call_history.keys():
                # Use internal unlocked version to avoid deadlock
                status = self._get_quota_status_unlocked(provider)

                calls = status["calls_in_window"]
                remaining = status["quota_remaining"]
                limit = status["quota_limit"]
                window = status["window_hours"]
                success = status["successful_calls"]
                failed = status["failed_calls"]

                msg = (
                    f"{provider}: {calls}/{limit} calls in {window}h window "
                    f"({success} success, {failed} failed) | "
                    f"Remaining: {remaining}"
                )

                # Add reset time info
                reset_time = status.get("reset_time")
                if reset_time:
                    reset_dt = datetime.fromisoformat(reset_time)
                    msg += f" | Resets: {reset_dt.strftime('%H:%M:%S')}"

                # Add warning for low quota
                quota_status = status["status"]
                if quota_status == "EXHAUSTED":
                    msg += " 🔴 EXHAUSTED!"
                elif quota_status == "CRITICAL":
                    msg += f" 🔴 CRITICAL: Only {remaining} calls left!"
                elif quota_status == "LOW":
                    msg += f" 🟡 LOW: {remaining} calls remaining"

                self.logger.log(log_level, msg)

    def check_quota_alerts(self) -> Dict[str, str]:
        """
        Check for quota-related alerts across all providers.

        Returns:
            Dictionary mapping provider names to alert messages
        """
        alerts = {}

        with self.lock:
            for provider in self.call_history.keys():
                # Use internal unlocked version to avoid deadlock
                status = self._get_quota_status_unlocked(provider)
                remaining = status["quota_remaining"]
                quota_status = status["status"]

                if quota_status == "EXHAUSTED":
                    alerts[provider] = "⛔ Quota exhausted! No API calls remaining."
                elif quota_status == "CRITICAL":
                    alerts[provider] = f"🔴 CRITICAL: Only {remaining} call(s) remaining!"
                elif quota_status == "LOW":
                    reset_time = status.get("reset_time")
                    reset_str = ""
                    if reset_time:
                        reset_dt = datetime.fromisoformat(reset_time)
                        reset_str = f" (resets at {reset_dt.strftime('%H:%M')})"
                    alerts[provider] = f"🟡 CAUTION: {remaining} calls remaining{reset_str}"

        return alerts

    def can_make_calls(self, provider: str, num_calls: int = 1) -> tuple[bool, str]:
        """
        Check if provider has sufficient quota to make N calls.

        Args:
            provider: Provider name
            num_calls: Number of calls we want to make

        Returns:
            Tuple of (can_proceed: bool, reason: str)
        """
        with self.lock:
            status = self._get_quota_status_unlocked(provider)
            remaining = status["quota_remaining"]

        if remaining >= num_calls:
            return True, f"OK: {remaining} calls available"
        elif remaining > 0:
            return False, (
                f"Insufficient quota: need {num_calls} calls, " f"only {remaining} remaining"
            )
        else:
            reset_time = status.get("reset_time")
            reset_str = ""
            if reset_time:
                reset_dt = datetime.fromisoformat(reset_time)
                reset_str = f" (resets at {reset_dt.strftime('%H:%M:%S')})"
            return False, f"Quota exhausted{reset_str}"


# Global tracker instance
_global_tracker: Optional[APIUsageTracker] = None
_tracker_lock = threading.Lock()


def get_global_tracker(persistence_dir: Optional[str] = None) -> APIUsageTracker:
    """
    Get or create the global API usage tracker instance.

    Args:
        persistence_dir: Directory for persisting usage data (only used on first call)

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
        quota_remaining: Reported quota remaining
        quota_limit: Reported quota limit
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
        provider: Provider name

    Returns:
        Dictionary with quota information
    """
    tracker = get_global_tracker()
    return tracker.get_quota_status(provider)


def can_make_calls(provider: str, num_calls: int = 1) -> tuple[bool, str]:
    """
    Check if provider has sufficient quota before making calls.

    Args:
        provider: Provider name
        num_calls: Number of calls needed

    Returns:
        Tuple of (can_proceed: bool, reason: str)
    """
    tracker = get_global_tracker()
    return tracker.can_make_calls(provider, num_calls)
