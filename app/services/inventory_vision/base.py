"""Inventory vision provider interface + error types."""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass

from app.services.inventory_vision.schemas import InventoryScanResult


class VisionProviderError(Exception):
    """Provider call failed (network, auth, timeout, refusal)."""

    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


class VisionResultError(VisionProviderError):
    """Provider responded, but the payload failed schema validation."""

    def __init__(self, message: str) -> None:
        super().__init__(message, retryable=True)


@dataclass(frozen=True)
class ScanImage:
    """One image to analyse: raw bytes + mime type."""

    data: bytes
    media_type: str = "image/jpeg"


class InventoryVisionProvider(ABC):
    """Analyses a batch of shelf/product photos into a validated structured result.

    Implementations must treat the whole batch as one scene (products can span
    overlapping photos) and must return only schema-valid data — the pipeline
    calls ``parse_scan_result`` regardless, and rejects anything invalid.
    """

    @abstractmethod
    async def analyse_images(self, images: Sequence[ScanImage]) -> InventoryScanResult:
        """Return the validated batch analysis. Raises VisionProviderError on failure."""
