import pytest

from app.services.delivery.base import DeliveryRequest, ProviderNotConfigured
from app.services.delivery.registry import enabled_providers, get_provider


def _req():
    return DeliveryRequest(
        pickup_address="Peaceway Pharmacy, Igando",
        dropoff_address="12 Church St, Ikotun",
        customer_phone="08030000000",
        package_description="1 item",
    )


def test_manual_always_enabled():
    assert get_provider("manual").enabled is True


def test_api_providers_disabled_without_keys():
    for key in ("kwik", "fez", "gokada", "custom"):
        assert get_provider(key).enabled is False


def test_enabled_providers_defaults_to_manual_only():
    keys = {p.key for p in enabled_providers()}
    assert keys == {"manual"}


async def test_manual_create_returns_reference():
    booking = await get_provider("manual").create_delivery(_req())
    assert booking.provider_delivery_id.startswith("MAN-")
    assert booking.provider_key == "manual"


async def test_unconfigured_api_provider_raises():
    with pytest.raises(ProviderNotConfigured):
        await get_provider("kwik").create_delivery(_req())
