"""Store and retrieve binary media (product photos today).

The Postgres backend is an implementation detail. Callers deal only in `MediaAsset`
UUIDs, so moving to object storage (Cloudflare R2 / S3) later means rewriting the
three functions here and nothing else.

Every image is normalized before storage, which is not cosmetic:

* **EXIF is stripped** by re-encoding. Phone photos carry GPS coordinates, and these
  images are served publicly — we are not publishing the pharmacy's location in the
  metadata of every product card.
* **Downscaled to 800px** on the long edge. A 4 MB phone photo becomes ~60 KB.
* **Re-encoded to WebP**, roughly half the bytes of equivalent JPEG.

Deduplication hashes the *normalized* output, so the same photo uploaded twice — or
uploaded once as JPEG and once as PNG — collapses to a single row.
"""
from __future__ import annotations

import hashlib
import io
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.media import MediaAsset

# Long-edge cap. Product cards render at 96-112px and the detail panel at ~350px, so
# 800 leaves room for retina without storing anything close to a full phone photo.
MAX_DIMENSION = 800
WEBP_QUALITY = 82
CONTENT_TYPE = "image/webp"

# Backstop only — normalization puts a realistic photo three orders of magnitude below
# this. Tripping it means something pathological arrived (a huge synthetic image), and
# we would rather reject than write it to the database.
MAX_STORED_BYTES = 2 * 1024 * 1024


class ImageRejected(ValueError):
    """Raised when the upload is not a usable image."""


def normalize_image(raw: bytes) -> tuple[bytes, int, int]:
    """Return (webp_bytes, width, height). Raises ImageRejected on unusable input."""
    try:
        from PIL import Image
    except ImportError as exc:  # pragma: no cover - Pillow is in requirements.txt
        raise ImageRejected("Image processing is unavailable on this server.") from exc

    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
    except Exception as exc:
        raise ImageRejected("That file could not be read as an image.") from exc

    # Re-encoding through a fresh RGB image is what actually drops EXIF/ICC metadata;
    # `img.info` is not carried over into the new object.
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="WEBP", quality=WEBP_QUALITY, method=6)
    out = buf.getvalue()

    if len(out) > MAX_STORED_BYTES:
        raise ImageRejected("That image is too large to store even after compression.")
    return out, img.width, img.height


async def store_image(
    db: AsyncSession, raw: bytes, uploaded_by: int | None = None
) -> MediaAsset:
    """Normalize and persist `raw`, reusing an existing row when the bytes match."""
    data, width, height = normalize_image(raw)
    digest = hashlib.sha256(data).hexdigest()

    existing = (
        await db.execute(select(MediaAsset).where(MediaAsset.sha256 == digest))
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    asset = MediaAsset(
        content_type=CONTENT_TYPE,
        sha256=digest,
        byte_size=len(data),
        width=width,
        height=height,
        data=data,
        uploaded_by_telegram_id=uploaded_by,
    )
    db.add(asset)
    await db.flush()
    return asset


async def get_asset(db: AsyncSession, asset_id: UUID) -> MediaAsset | None:
    return (
        await db.execute(select(MediaAsset).where(MediaAsset.id == asset_id))
    ).scalar_one_or_none()
