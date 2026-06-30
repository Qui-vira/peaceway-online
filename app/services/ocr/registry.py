"""Returns the configured OCR provider (Tesseract default, Cloud if env-gated)."""
from __future__ import annotations

import os

from app.services.ocr.base import OcrProvider


def get_provider() -> OcrProvider:
    if os.getenv("OCR_PROVIDER", "tesseract").lower() == "cloud":
        api_key = os.getenv("GOOGLE_VISION_API_KEY", "")
        if api_key:
            from app.services.ocr.cloud import CloudOcrProvider
            return CloudOcrProvider(api_key)
    from app.services.ocr.tesseract import TesseractProvider
    return TesseractProvider()
