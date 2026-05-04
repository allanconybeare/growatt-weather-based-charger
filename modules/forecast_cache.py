"""API response caching to minimize external API calls."""

import hashlib
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ForecastCache:
    """
    File-based cache for forecast API responses.

    Cache keys are based on: provider + date + array config hash
    TTL ensures stale data is refreshed.
    """

    def __init__(
        self,
        cache_dir: str,
        default_ttl_hours: float = 4.0,
        enabled: bool = True,
    ):
        """
        Initialize the forecast cache.

        Args:
            cache_dir: Directory to store cache files
            default_ttl_hours: How long cached data remains valid
            enabled: Whether caching is enabled
        """

        # Use module name - automatically inherits from configured root logger
        self.logger = logging.getLogger(__name__)

        self.cache_dir = Path(cache_dir)
        self.default_ttl_hours = default_ttl_hours
        self.enabled = enabled

        if self.enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.logger.info(
                f"Forecast cache initialized: {self.cache_dir} (TTL: {default_ttl_hours}h)"
            )

    def _get_cache_key(
        self,
        provider: str,
        target_date: datetime,
        config_hash: Optional[str] = None,
    ) -> str:
        """Generate a unique cache key."""
        date_str = target_date.strftime("%Y-%m-%d")
        key = f"{provider}_{date_str}"
        if config_hash:
            key += f"_{config_hash[:8]}"
        return key

    def _get_cache_path(self, cache_key: str) -> Path:
        """Get the file path for a cache key."""
        return self.cache_dir / f"{cache_key}.json"

    def _hash_config(self, config: Dict[str, Any]) -> str:
        """Create a hash of array configuration for cache key."""
        config_str = json.dumps(config, sort_keys=True)
        return hashlib.md5(config_str.encode()).hexdigest()

    def get(
        self,
        provider: str,
        target_date: datetime,
        array_config: Optional[Dict] = None,
        ttl_hours: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached forecast data if valid.

        Args:
            provider: Provider name (e.g., "forecast.solar", "solcast")
            target_date: Date the forecast is for
            array_config: Array configuration (for multi-array setups)
            ttl_hours: Override default TTL

        Returns:
            Cached data dict or None if cache miss/expired
        """
        if not self.enabled:
            return None

        config_hash = self._hash_config(array_config) if array_config else None
        cache_key = self._get_cache_key(provider, target_date, config_hash)
        cache_path = self._get_cache_path(cache_key)

        if not cache_path.exists():
            self.logger.debug(f"Cache miss: {cache_key}")
            return None

        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cached = json.load(f)

            # Check TTL
            cached_time = datetime.fromisoformat(cached["cached_at"])
            ttl = ttl_hours or self.default_ttl_hours
            expiry = cached_time + timedelta(hours=ttl)

            if datetime.now() > expiry:
                self.logger.debug(f"Cache expired: {cache_key} (cached at {cached_time})")
                cache_path.unlink()  # Remove expired cache
                return None

            age_minutes = (datetime.now() - cached_time).total_seconds() / 60
            self.logger.info(
                f"Cache hit: {provider} forecast for {target_date.strftime('%Y-%m-%d')} "
                f"(age: {age_minutes:.0f}m)"
            )
            return cached["data"]

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            self.logger.warning(f"Invalid cache file {cache_key}: {e}")
            cache_path.unlink(missing_ok=True)
            return None

    def set(
        self,
        provider: str,
        target_date: datetime,
        data: Dict[str, Any],
        array_config: Optional[Dict] = None,
    ) -> None:
        """
        Store forecast data in cache.

        Args:
            provider: Provider name
            target_date: Date the forecast is for
            data: Forecast data to cache
            array_config: Array configuration (for cache key)
        """
        if not self.enabled:
            return

        config_hash = self._hash_config(array_config) if array_config else None
        cache_key = self._get_cache_key(provider, target_date, config_hash)
        cache_path = self._get_cache_path(cache_key)

        cache_entry = {
            "cached_at": datetime.now().isoformat(),
            "provider": provider,
            "target_date": target_date.strftime("%Y-%m-%d"),
            "config_hash": config_hash,
            "data": data,
        }

        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(cache_entry, f, indent=2, default=str)
            self.logger.info(f"Cached {provider} forecast for {target_date.strftime('%Y-%m-%d')}")
        except Exception as e:
            self.logger.error(f"Failed to write cache {cache_key}: {e}")

    def invalidate(
        self,
        provider: Optional[str] = None,
        target_date: Optional[datetime] = None,
    ) -> int:
        """
        Invalidate (delete) cached entries.

        Args:
            provider: If set, only invalidate this provider's cache
            target_date: If set, only invalidate this date's cache

        Returns:
            Number of cache entries invalidated
        """
        if not self.enabled:
            return 0

        count = 0
        pattern = "*.json"

        if provider and target_date:
            date_str = target_date.strftime("%Y-%m-%d")
            pattern = f"{provider}_{date_str}*.json"
        elif provider:
            pattern = f"{provider}_*.json"
        elif target_date:
            date_str = target_date.strftime("%Y-%m-%d")
            pattern = f"*_{date_str}*.json"

        for cache_file in self.cache_dir.glob(pattern):
            cache_file.unlink()
            count += 1
            self.logger.debug(f"Invalidated cache: {cache_file.name}")

        if count > 0:
            self.logger.info(f"Invalidated {count} cache entries")
        return count

    def clear_all(self) -> int:
        """Clear all cached data."""
        return self.invalidate()

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if not self.enabled or not self.cache_dir.exists():
            return {"enabled": False}

        cache_files = list(self.cache_dir.glob("*.json"))
        total_size = sum(f.stat().st_size for f in cache_files)

        return {
            "enabled": True,
            "cache_dir": str(self.cache_dir),
            "entries": len(cache_files),
            "total_size_kb": total_size / 1024,
            "ttl_hours": self.default_ttl_hours,
        }
