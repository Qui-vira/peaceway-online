"""OCR provider interface."""
from __future__ import annotations

from abc import ABC, abstractmethod


class OcrProvider(ABC):
    @abstractmethod
    async def extract_text(self, image_bytes: bytes) -> str:
        """Return extracted text from image bytes, or empty string on failure."""
