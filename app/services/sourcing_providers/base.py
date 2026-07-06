"""Base types for partner sourcing providers."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.models import PartnerChannel


class PartnerSourcingProvider(Protocol):
    channel: PartnerChannel

    async def send_sourcing_request(self, request: "SourcingDispatchRequest") -> dict:
        ...


@dataclass(slots=True)
class SourcingDispatchRequest:
    order_id: UUID
    order_code: str
    partner_key: str
    payload: dict


class ProviderNotConfigured(RuntimeError):
    """Raised when a provider exists conceptually but lacks real credentials/config."""
