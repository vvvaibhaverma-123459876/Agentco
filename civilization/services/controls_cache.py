"""
Civilization layer — Controls cache with file-change invalidation.

Caches controls.yaml in memory and automatically reloads on file change.
"""
from __future__ import annotations

import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml


class ControlsCache:
    """Thread-safe cache for controls.yaml with automatic invalidation."""

    def __init__(self, controls_file: Path):
        self.controls_file = controls_file
        self._cache: Optional[dict] = None
        self._cache_time: Optional[datetime] = None
        self._file_mtime: Optional[float] = None
        self._lock = threading.RLock()
        self._load_cache()

    def _load_cache(self) -> None:
        """Load controls.yaml from disk."""
        try:
            with open(self.controls_file) as f:
                self._cache = yaml.safe_load(f) or {}
            self._cache_time = datetime.now(timezone.utc)
            if self.controls_file.exists():
                self._file_mtime = self.controls_file.stat().st_mtime
        except Exception as e:
            self._cache = {}
            raise RuntimeError(f"Error loading controls.yaml: {e}")

    def _invalidate_if_changed(self) -> None:
        """Check if file changed and reload if needed."""
        if not self.controls_file.exists():
            return

        try:
            current_mtime = self.controls_file.stat().st_mtime
            if self._file_mtime is None or current_mtime != self._file_mtime:
                self._load_cache()
        except Exception:
            # On error, keep using stale cache
            pass

    def get(self) -> dict:
        """Get current controls, reloading if file changed."""
        with self._lock:
            self._invalidate_if_changed()
            return self._cache.copy() if self._cache else {}

    def get_setting(self, key: str, default: any = None) -> any:
        """Get specific control setting with default."""
        with self._lock:
            self._invalidate_if_changed()
            return self._cache.get(key, default) if self._cache else default
