"""Inventory vision providers: batch photo analysis -> validated structured result."""
from app.services.inventory_vision.base import (
    InventoryVisionProvider,
    VisionProviderError,
    VisionResultError,
)
from app.services.inventory_vision.registry import get_provider
from app.services.inventory_vision.schemas import (
    DetectedProduct,
    InventoryScanResult,
    parse_scan_result,
)

__all__ = [
    "InventoryVisionProvider",
    "VisionProviderError",
    "VisionResultError",
    "get_provider",
    "DetectedProduct",
    "InventoryScanResult",
    "parse_scan_result",
]
