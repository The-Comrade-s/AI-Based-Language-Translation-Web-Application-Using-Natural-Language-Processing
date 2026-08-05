"""
ai/model_manager.py
====================
Loads and caches the AI translation models. NLLB-200 (primary) is a
single multilingual model capable of translating between any pair of its
200 supported languages directly. MarianMT (fallback) is per-language-pair
and is loaded on demand only if the primary model fails.

Model loading is intentionally isolated behind small, overridable methods
(`_load_primary_model`, `_load_marian_model`) so the orchestration logic
in `translate()` can be exercised in tests without downloading real model
weights — tests can monkeypatch those two methods directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock

from config import settings, MODELS_CACHE_DIR
from utils.exceptions import ModelLoadError, TranslationError
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class LoadedModel:
    tokenizer: object
    model: object
    device: str


class ModelManager:
    """Lazily loads and caches translation models. One instance is shared
    application-wide via `get_model_manager()` below."""

    def __init__(self) -> None:
        self._primary: LoadedModel | None = None
        self._marian_cache: dict[str, LoadedModel] = {}
        self._lock = Lock()
        self._device: str | None = None

    # ----------------------------------------------------------------
    # Device selection
    # ----------------------------------------------------------------

    def get_device(self) -> str:
        """Return 'cuda' if a GPU is available and not disabled, else 'cpu'.
        Result is computed once and cached for the lifetime of the process."""
        if self._device is not None:
            return self._device

        if settings.force_cpu:
            self._device = "cpu"
            return self._device

        try:
            import torch

            self._device = "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            self._device = "cpu"

        logger.info("Translation device selected: %s", self._device)
        return self._device

    # ----------------------------------------------------------------
    # Primary model (NLLB-200)
    # ----------------------------------------------------------------

    def _load_primary_model(self) -> LoadedModel:
        """Load NLLB-200 from Hugging Face (or local cache if already
        downloaded). This is the only method that touches disk/network
        for the primary model, so it can be mocked in tests."""
        try:
            from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
        except ImportError as exc:
            raise ModelLoadError(
                f"transformers/torch not installed: {exc}",
                user_message="Translation engine is not installed correctly.",
            ) from exc

        model_name = settings.primary_model_name
        device = self.get_device()

        try:
            logger.info("Loading primary model '%s' on device '%s'...", model_name, device)
            tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=str(MODELS_CACHE_DIR))
            model = AutoModelForSeq2SeqLM.from_pretrained(model_name, cache_dir=str(MODELS_CACHE_DIR))
            model.to(device)
            model.eval()
        except Exception as exc:  # noqa: BLE001 - any load failure must degrade gracefully
            raise ModelLoadError(
                f"Failed to load primary model '{model_name}': {exc}",
                user_message="The primary translation model could not be loaded.",
            ) from exc

        logger.info("Primary model loaded successfully: %s", model_name)
        return LoadedModel(tokenizer=tokenizer, model=model, device=device)

    def get_primary_model(self) -> LoadedModel:
        """Return the cached primary model, loading it on first use."""
        if self._primary is not None:
            return self._primary

        with self._lock:
            if self._primary is None:  # re-check inside the lock
                self._primary = self._load_primary_model()
        return self._primary

    # ----------------------------------------------------------------
    # Fallback model (MarianMT, per language pair)
    # ----------------------------------------------------------------

    def _load_marian_model(self, src_iso: str, tgt_iso: str) -> LoadedModel:
        try:
            from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
        except ImportError as exc:
            raise ModelLoadError(
                f"transformers/torch not installed: {exc}",
                user_message="Translation engine is not installed correctly.",
            ) from exc

        model_name = settings.fallback_model_name.format(src=src_iso, tgt=tgt_iso)
        device = self.get_device()

        try:
            logger.info("Loading fallback model '%s'...", model_name)
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
            model.to(device)
            model.eval()
        except Exception as exc:  # noqa: BLE001
            raise ModelLoadError(
                f"Failed to load fallback model '{model_name}': {exc}",
                user_message="No translation model is available for this language pair.",
            ) from exc

        return LoadedModel(tokenizer=tokenizer, model=model, device=device)

    def get_marian_model(self, src_iso: str, tgt_iso: str) -> LoadedModel:
        """Return a cached MarianMT model for this specific language pair,
        loading it on first use. Each pair is cached independently."""
        key = f"{src_iso}-{tgt_iso}"
        if key in self._marian_cache:
            return self._marian_cache[key]

        with self._lock:
            if key not in self._marian_cache:
                self._marian_cache[key] = self._load_marian_model(src_iso, tgt_iso)
        return self._marian_cache[key]

    # ----------------------------------------------------------------
    # Inference
    # ----------------------------------------------------------------

    def generate_nllb(self, text: str, src_nllb_code: str, tgt_nllb_code: str, max_length: int = 512) -> str:
        """Run NLLB-200 inference for a single piece of text."""
        loaded = self.get_primary_model()
        tokenizer, model = loaded.tokenizer, loaded.model

        try:
            tokenizer.src_lang = src_nllb_code
            inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=max_length).to(loaded.device)
            forced_bos_token_id = tokenizer.convert_tokens_to_ids(tgt_nllb_code)

            import torch

            with torch.no_grad():
                generated = model.generate(
                    **inputs,
                    forced_bos_token_id=forced_bos_token_id,
                    max_length=max_length,
                )
            return tokenizer.batch_decode(generated, skip_special_tokens=True)[0]
        except Exception as exc:  # noqa: BLE001
            raise TranslationError(
                f"NLLB inference failed ({src_nllb_code}->{tgt_nllb_code}): {exc}",
                user_message="Translation failed. Please try again.",
            ) from exc

    def generate_marian(self, text: str, src_iso: str, tgt_iso: str, max_length: int = 512) -> str:
        """Run MarianMT inference for a single piece of text (fallback path)."""
        loaded = self.get_marian_model(src_iso, tgt_iso)
        tokenizer, model = loaded.tokenizer, loaded.model

        try:
            inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=max_length).to(loaded.device)

            import torch

            with torch.no_grad():
                generated = model.generate(**inputs, max_length=max_length)
            return tokenizer.batch_decode(generated, skip_special_tokens=True)[0]
        except Exception as exc:  # noqa: BLE001
            raise TranslationError(
                f"MarianMT inference failed ({src_iso}->{tgt_iso}): {exc}",
                user_message="Translation failed. Please try again.",
            ) from exc


_manager_instance: ModelManager | None = None
_manager_lock = Lock()


def get_model_manager() -> ModelManager:
    """Return the process-wide singleton ModelManager."""
    global _manager_instance
    if _manager_instance is None:
        with _manager_lock:
            if _manager_instance is None:
                _manager_instance = ModelManager()
    return _manager_instance
