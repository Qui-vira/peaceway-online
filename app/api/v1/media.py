"""Serve stored media assets (product photos).

Assets are immutable — replacing a product's photo writes a new row with a new id —
so responses are cached aggressively and revalidated with a strong ETag.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Header, Response, status

from app.api.deps import DbSession
from app.services import file_storage

router = APIRouter(tags=["media"])

# Safe to cache forever: the URL contains the asset id, and assets never change in place.
CACHE_CONTROL = "public, max-age=31536000, immutable"


def asset_url(asset_id: UUID | None) -> str | None:
    """Public path for a stored asset, or None.

    Defined beside the route so the URL shape has exactly one source of truth; the
    catalog and admin serializers both call this rather than formatting their own.
    """
    return f"/api/v1/media/{asset_id}" if asset_id else None


@router.get("/media/{asset_id}")
async def get_media(
    asset_id: UUID,
    db: DbSession,
    if_none_match: str | None = Header(None, alias="If-None-Match"),
) -> Response:
    """Return the raw bytes of a stored asset."""
    asset = await file_storage.get_asset(db, asset_id)
    if asset is None:
        return Response(status_code=status.HTTP_404_NOT_FOUND)

    etag = f'"{asset.sha256}"'
    headers = {"Cache-Control": CACHE_CONTROL, "ETag": etag}

    # A client that already holds these bytes gets a 304 instead of the payload.
    if if_none_match and etag in [tag.strip() for tag in if_none_match.split(",")]:
        return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=headers)

    return Response(content=asset.data, media_type=asset.content_type, headers=headers)
