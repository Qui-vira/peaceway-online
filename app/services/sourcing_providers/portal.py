"""Portal-backed sourcing provider.

Portal partners do not have their own API; Peaceway records the sourcing request
for portal users to review in the app.
"""
from __future__ import annotations

from app.models import PartnerChannel
from app.services.sourcing_providers.base import SourcingDispatchRequest


class PortalPartnerProvider:
    channel = PartnerChannel.PORTAL

    async def send_sourcing_request(self, request: SourcingDispatchRequest) -> dict:
        return {
            "ok": True,
            "mode": "portal",
            "partner_key": request.partner_key,
            "order_code": request.order_code,
        }
