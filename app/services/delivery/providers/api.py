"""Official-API logistics providers (Kwik, Fez, Gokada, Custom).

Each provider is ENABLED only when its API key is configured. Until then it stays
disabled and is never offered to customers/staff.

The actual HTTP calls must be implemented against each partner's OFFICIAL,
documented API (request/response shapes, auth, endpoints). Those specs are not
bundled here, so the call methods raise ProviderNotConfigured at the clearly-marked
integration point. Wiring a real partner = filling in `_client()` + the three
methods using their published API docs. Do NOT scrape or reverse-engineer apps.
"""
from __future__ import annotations

from app.core.config import get_settings
from app.services.delivery.base import (
    BookingResult,
    DeliveryProvider,
    DeliveryRequest,
    ProviderNotConfigured,
    QuoteResult,
    StatusResult,
)


class _ApiProvider(DeliveryProvider):
    """Shared scaffold for credential-gated official-API providers."""

    env_key_attr: str = ""  # name of the Settings attribute holding the API key
    base_url: str = ""

    @property
    def api_key(self) -> str:
        return getattr(get_settings(), self.env_key_attr, "") or ""

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def _require_endpoints(self):
        raise ProviderNotConfigured(
            f"{self.name} official API not wired yet. Add its documented endpoints "
            f"(auth, quote, create, status) per the partner's API docs, then implement "
            f"estimate_fee/create_delivery/get_status. Credentials present: {self.enabled}."
        )

    async def estimate_fee(self, request: DeliveryRequest) -> QuoteResult:
        self._require_endpoints()

    async def create_delivery(self, request: DeliveryRequest) -> BookingResult:
        self._require_endpoints()

    async def get_status(self, provider_delivery_id: str) -> StatusResult:
        self._require_endpoints()


class KwikProvider(_ApiProvider):
    key = "kwik"
    name = "Kwik"
    supports_gps = True
    supports_tracking_url = True
    env_key_attr = "kwik_api_key"
    base_url = "https://api.kwik.delivery"  # confirm against official Kwik API docs


class FezProvider(_ApiProvider):
    key = "fez"
    name = "Fez Delivery"
    supports_gps = False
    supports_tracking_url = True
    env_key_attr = "fez_api_key"
    base_url = "https://api.fezdelivery.co"  # confirm against official Fez API docs


class GokadaProvider(_ApiProvider):
    key = "gokada"
    name = "Gokada"
    supports_gps = True
    supports_tracking_url = True
    env_key_attr = "gokada_api_key"
    base_url = "https://api.gokada.ng"  # confirm against official Gokada API docs


class CustomProvider(_ApiProvider):
    key = "custom"
    name = "Custom Provider"
    supports_gps = True
    supports_tracking_url = True
    env_key_attr = "custom_api_key"
    base_url = ""  # set per integration
