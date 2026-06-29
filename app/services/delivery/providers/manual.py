"""Manual dispatcher provider — the always-available Phase 1/2 default.

No external API. Fees come from the order's delivery zone (computed elsewhere),
bookings produce a local reference, and status is driven by staff buttons.
"""
from __future__ import annotations

import secrets
from decimal import Decimal

from app.services.delivery.base import (
    BookingResult,
    DeliveryProvider,
    DeliveryRequest,
    QuoteResult,
    StatusResult,
)


class ManualProvider(DeliveryProvider):
    key = "manual"
    name = "Manual Dispatcher"
    supports_gps = False
    supports_tracking_url = False

    @property
    def enabled(self) -> bool:
        return True

    async def estimate_fee(self, request: DeliveryRequest) -> QuoteResult:
        # Manual fee is the zone fee, set by admin; we return 0 here and let the
        # caller use the order's zone fee. Kept for interface symmetry.
        return QuoteResult(provider_key=self.key, fee=Decimal("0"), eta_minutes=None)

    async def create_delivery(self, request: DeliveryRequest) -> BookingResult:
        ref = "MAN-" + "".join(secrets.choice("0123456789") for _ in range(6))
        return BookingResult(
            provider_key=self.key,
            provider_delivery_id=ref,
            status="RIDER_ASSIGNED",
        )

    async def get_status(self, provider_delivery_id: str) -> StatusResult:
        # Manual status is whatever staff last set on the order; nothing to poll.
        return StatusResult(provider_key=self.key, status="MANUAL")
