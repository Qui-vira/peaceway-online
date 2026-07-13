"""Provider registry - resolves provider instances and lists enabled ones."""
from __future__ import annotations

from app.services.delivery.base import DeliveryProvider
from app.services.delivery.providers.api import (
    CustomProvider,
    FezProvider,
    GokadaProvider,
    KwikProvider,
)
from app.services.delivery.providers.manual import ManualProvider

# Instantiate once; providers are stateless (config read lazily).
_PROVIDERS: dict[str, DeliveryProvider] = {
    p.key: p
    for p in (
        ManualProvider(),
        KwikProvider(),
        FezProvider(),
        GokadaProvider(),
        CustomProvider(),
    )
}


def get_provider(key: str) -> DeliveryProvider | None:
    return _PROVIDERS.get(key)


def all_providers() -> list[DeliveryProvider]:
    return list(_PROVIDERS.values())


def enabled_providers() -> list[DeliveryProvider]:
    """Manual is always enabled; API providers only when credentialed."""
    return [p for p in _PROVIDERS.values() if p.enabled]
