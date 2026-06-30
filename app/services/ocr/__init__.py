"""Pluggable OCR provider system. Default: Tesseract. Optional: Cloud (env-gated)."""
from app.services.ocr.registry import get_provider

__all__ = ["get_provider"]
