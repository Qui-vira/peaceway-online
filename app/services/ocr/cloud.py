"""Cloud OCR provider (Google Vision) — disabled until OCR_PROVIDER=cloud is set."""
from __future__ import annotations

import base64

from app.core.logging import get_logger
from app.services.ocr.base import OcrProvider

log = get_logger("ocr.cloud")


class CloudOcrProvider(OcrProvider):
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def extract_text(self, image_bytes: bytes) -> str:
        try:
            import httpx
        except ImportError:
            return ""
        b64 = base64.b64encode(image_bytes).decode()
        payload = {
            "requests": [
                {
                    "image": {"content": b64},
                    "features": [{"type": "TEXT_DETECTION"}],
                }
            ]
        }
        url = f"https://vision.googleapis.com/v1/images:annotate?key={self._api_key}"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                annotations = data["responses"][0].get("textAnnotations", [])
                return annotations[0]["description"].strip() if annotations else ""
        except Exception as exc:  # noqa: BLE001
            log.error("cloud_ocr_failed", error=str(exc))
            return ""
