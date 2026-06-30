"""Tesseract OCR provider — free, local, requires system tesseract-ocr package."""
from __future__ import annotations

import asyncio
import io

from app.core.logging import get_logger
from app.services.ocr.base import OcrProvider

log = get_logger("ocr.tesseract")


class TesseractProvider(OcrProvider):
    async def extract_text(self, image_bytes: bytes) -> str:
        try:
            import pytesseract  # type: ignore[import]
            from PIL import Image  # type: ignore[import]
        except ImportError:
            log.warning("tesseract_unavailable", reason="pytesseract or Pillow not installed")
            return ""
        try:
            image = Image.open(io.BytesIO(image_bytes))
            loop = asyncio.get_event_loop()
            text: str = await loop.run_in_executor(
                None, lambda: pytesseract.image_to_string(image)
            )
            return text.strip()
        except Exception as exc:  # noqa: BLE001
            log.error("tesseract_failed", error=str(exc))
            return ""
