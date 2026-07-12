"""Returns the configured inventory vision provider (Anthropic by default)."""
from __future__ import annotations

from app.core.config import get_settings
from app.services.inventory_vision.base import InventoryVisionProvider, VisionProviderError


def get_provider() -> InventoryVisionProvider:
    settings = get_settings()
    name = (settings.inventory_vision_provider or "anthropic").lower()
    if name == "anthropic":
        if not settings.anthropic_api_key:
            raise VisionProviderError(
                "AI inventory scanning is not configured: set ANTHROPIC_API_KEY."
            )
        from app.services.inventory_vision.anthropic_provider import AnthropicVisionProvider

        return AnthropicVisionProvider(
            api_key=settings.anthropic_api_key,
            model=settings.inventory_vision_model,
        )
    raise VisionProviderError(f"Unknown inventory vision provider: {name}")
