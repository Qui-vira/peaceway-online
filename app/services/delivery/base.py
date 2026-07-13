"""Logistics provider interface.

Every provider (manual or official-API-backed) implements the same contract so the
rest of the app never depends on a specific logistics company. New partners are
added by writing one subclass - no other code changes.

IMPORTANT: API-backed providers must use each partner's OFFICIAL, documented API
only. No scraping, no reverse-engineering of private/mobile endpoints.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal


@dataclass
class DeliveryRequest:
    pickup_address: str
    dropoff_address: str
    customer_phone: str
    package_description: str
    customer_name: str | None = None
    area: str | None = None
    landmark: str | None = None


@dataclass
class QuoteResult:
    provider_key: str
    fee: Decimal
    eta_minutes: int | None = None
    raw: dict = field(default_factory=dict)


@dataclass
class BookingResult:
    provider_key: str
    provider_delivery_id: str | None
    status: str
    tracking_url: str | None = None
    raw: dict = field(default_factory=dict)


@dataclass
class StatusResult:
    provider_key: str
    status: str  # mapped to DeliveryStatus value where possible
    rider_name: str | None = None
    rider_phone: str | None = None
    tracking_url: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    raw: dict = field(default_factory=dict)


class DeliveryProvider(ABC):
    """Base class for all logistics providers."""

    key: str = "base"
    name: str = "Base Provider"
    supports_gps: bool = False
    supports_tracking_url: bool = False

    @property
    @abstractmethod
    def enabled(self) -> bool:
        """A provider is enabled only when it can actually be used.

        Manual is always enabled; API providers are enabled only when valid
        credentials are configured.
        """

    @abstractmethod
    async def estimate_fee(self, request: DeliveryRequest) -> QuoteResult: ...

    @abstractmethod
    async def create_delivery(self, request: DeliveryRequest) -> BookingResult: ...

    @abstractmethod
    async def get_status(self, provider_delivery_id: str) -> StatusResult: ...

    async def cancel(self, provider_delivery_id: str) -> bool:
        return True


class ProviderNotConfigured(RuntimeError):
    """Raised when an API provider is used without valid credentials/endpoints."""
