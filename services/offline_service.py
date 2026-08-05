"""
services/offline_service.py
============================
Reports on which AI models are already downloaded to local disk (and
therefore usable without internet access) and allows removing them.

Note on architecture: NLLB-200 is a single multilingual model — unlike
the older per-language-pair MarianMT approach, there is no separate
model to "download" per language once the primary model is cached.
Offline capability in ALT is therefore primarily "is the primary model
cached locally", plus any MarianMT fallback models used so far.
"""

from __future__ import annotations

from pathlib import Path

from config import settings, MODELS_CACHE_DIR
from utils.logger import get_logger

logger = get_logger(__name__)


class OfflineService:
    """Inspects the local Hugging Face cache directory to report which
    models are already downloaded."""

    def _dir_size_mb(self, path: Path) -> float:
        total = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
        return round(total / (1024 * 1024), 2)

    def list_cached_models(self) -> list[dict]:
        """Return metadata for every model snapshot found in the local
        cache directory. Hugging Face's cache layout stores each model
        under a folder named `models--<org>--<model-name>`."""
        if not MODELS_CACHE_DIR.exists():
            return []

        results = []
        for entry in MODELS_CACHE_DIR.iterdir():
            if not entry.is_dir() or not entry.name.startswith("models--"):
                continue
            model_name = entry.name.removeprefix("models--").replace("--", "/")
            results.append(
                {
                    "name": model_name,
                    "size_mb": self._dir_size_mb(entry),
                    "path": str(entry),
                }
            )
        return results

    def is_primary_model_cached(self) -> bool:
        """Check whether the configured primary model (NLLB-200) has
        already been downloaded to local disk."""
        expected_dir_name = "models--" + settings.primary_model_name.replace("/", "--")
        return (MODELS_CACHE_DIR / expected_dir_name).exists()

    def delete_cached_model(self, model_name: str) -> bool:
        """Delete a specific cached model by its Hugging Face name (e.g.
        'facebook/nllb-200-distilled-600M'). Returns True if it was found
        and removed."""
        import shutil

        expected_dir_name = "models--" + model_name.replace("/", "--")
        target = MODELS_CACHE_DIR / expected_dir_name
        if not target.exists():
            return False

        shutil.rmtree(target)
        logger.info("Deleted cached model: %s", model_name)
        return True

    def offline_readiness(self) -> dict:
        """Summarize whether ALT can currently translate without
        internet access."""
        primary_cached = self.is_primary_model_cached()
        return {
            "primary_model": settings.primary_model_name,
            "primary_model_cached": primary_cached,
            "offline_ready": primary_cached,
            "cached_models": self.list_cached_models(),
        }
