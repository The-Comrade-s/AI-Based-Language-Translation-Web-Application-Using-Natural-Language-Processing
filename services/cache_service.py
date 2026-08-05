"""
services/cache_service.py
==========================
Clears various on-disk caches (temp files, model cache) and reports
their size. Streamlit's own `st.cache_resource`/`st.cache_data` caches
are cleared separately by the page layer (they require `st.cache_*.clear()`
calls, which only make sense inside a running Streamlit session).
"""

from __future__ import annotations

import shutil

from config import MODELS_CACHE_DIR, TEMP_DIR
from utils.logger import get_logger

logger = get_logger(__name__)


class CacheManager:
    """Clears and reports on ALT's on-disk caches."""

    def clear_temp_files(self) -> int:
        """Delete everything in the temp directory. Returns the number
        of files removed."""
        return self._clear_directory(TEMP_DIR)

    def clear_model_cache(self) -> int:
        """Delete all downloaded model weights. The next translation
        request will re-download them — use with caution."""
        return self._clear_directory(MODELS_CACHE_DIR)

    def _clear_directory(self, path) -> int:
        if not path.exists():
            return 0

        removed = 0
        for item in path.iterdir():
            if item.name == ".gitkeep":
                continue
            try:
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
                removed += 1
            except OSError:
                logger.exception("Failed to remove cache item: %s", item)

        logger.info("Cleared %d item(s) from %s", removed, path)
        return removed
