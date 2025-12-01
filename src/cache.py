"""
Simple file-based caching for API responses.
"""

import json
import logging
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Optional


logger = logging.getLogger(__name__)


class Cache:
    """Simple JSON-based cache with TTL support."""

    def __init__(self, cache_dir: str = ".cache", ttl_hours: int = 24):
        """
        Initialize cache.

        Args:
            cache_dir: Directory for cache files
            ttl_hours: Time-to-live in hours (default: 24)
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.ttl = timedelta(hours=ttl_hours)
        self.enabled = True

    def _get_cache_path(self, key: str) -> Path:
        """
        Get cache file path for a key.

        Args:
            key: Cache key

        Returns:
            Path to cache file
        """
        # Hash the key to create a safe filename
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.json"

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found or expired
        """
        if not self.enabled:
            return None

        cache_path = self._get_cache_path(key)

        if not cache_path.exists():
            logger.debug(f"Cache miss: {key}")
            return None

        try:
            with open(cache_path, 'r') as f:
                cache_data = json.load(f)

            # Check if expired
            cached_at = datetime.fromisoformat(cache_data['cached_at'])
            if datetime.now() - cached_at > self.ttl:
                logger.debug(f"Cache expired: {key}")
                cache_path.unlink()  # Delete expired cache
                return None

            logger.debug(f"Cache hit: {key}")
            return cache_data['value']

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Invalid cache file for {key}: {e}")
            cache_path.unlink()  # Delete corrupted cache
            return None

    def set(self, key: str, value: Any):
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache (must be JSON-serializable)
        """
        if not self.enabled:
            return

        cache_path = self._get_cache_path(key)

        cache_data = {
            'key': key,
            'cached_at': datetime.now().isoformat(),
            'value': value
        }

        try:
            with open(cache_path, 'w') as f:
                json.dump(cache_data, f, indent=2)
            logger.debug(f"Cached: {key}")
        except (TypeError, ValueError) as e:
            logger.warning(f"Could not cache {key}: {e}")

    def clear(self):
        """Clear all cache files."""
        count = 0
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()
            count += 1
        logger.info(f"Cleared {count} cache files")

    def get_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dict with cache stats
        """
        cache_files = list(self.cache_dir.glob("*.json"))
        total_size = sum(f.stat().st_size for f in cache_files)

        return {
            'files': len(cache_files),
            'size_bytes': total_size,
            'size_mb': total_size / 1024 / 1024,
            'enabled': self.enabled,
        }

    def disable(self):
        """Disable caching."""
        self.enabled = False
        logger.info("Cache disabled")

    def enable(self):
        """Enable caching."""
        self.enabled = True
        logger.info("Cache enabled")
