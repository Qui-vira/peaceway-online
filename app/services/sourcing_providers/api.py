"""API-backed sourcing provider.

This is intentionally conservative: if a real partner endpoint is not configured,
we fail loudly instead of pretending an integration exists.
"""
from __future__ import annotations

import httpx

from app.models import PartnerChannel
from app.services.sourcing_providers.base import ProviderNotConfigured, SourcingDispatchRequest


class ApiPartnerProvider:
    channel = PartnerChannel.API

    def __init__(self, *, base_url: str | None):
        self.base_url = base_url.rstrip("/") if base_url else None

    async def send_sourcing_request(self, request: SourcingDispatchRequest) -> dict:
        if not self.base_url:
            raise ProviderNotConfigured("Partner API base URL is not configured.")
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"{self.base_url}/sourcing-requests",
                json=request.payload,
            )
            response.raise_for_status()
            return response.json() if response.content else {"ok": True}
