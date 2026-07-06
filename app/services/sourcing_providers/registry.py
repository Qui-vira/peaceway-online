"""Resolve sourcing providers by partner channel."""
from __future__ import annotations

from app.models import NetworkPartner, PartnerChannel
from app.services.sourcing_providers.api import ApiPartnerProvider
from app.services.sourcing_providers.portal import PortalPartnerProvider


def get_provider(partner: NetworkPartner):
    if partner.channel_type == PartnerChannel.API:
        return ApiPartnerProvider(base_url=partner.api_base_url)
    return PortalPartnerProvider()
