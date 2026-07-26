"""Binary media assets stored in Postgres and served by app.api.v1.media.

Product photos are the only producer today. Bytes live in the `data` BYTEA column
because this deployment has nowhere else to put them — no object storage, no Railway
volume, no writable runtime directory (Railway and Vercel filesystems are both
ephemeral). At the expected volume (one photo per product, ~60 KB each after
normalization) that is comfortably within Postgres.

`app.services.file_storage` is the only module that should touch `data` directly; it
is the swap point if this ever moves to S3/R2 — the column becomes a key/URL and
nothing else in the codebase changes, because everywhere else refers to an asset by
its UUID.
"""
from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import BigInteger, Integer, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class MediaAsset(Base, TimestampMixin):
    """One stored image. Immutable once written — re-uploading creates a new row."""

    __tablename__ = "media_assets"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    content_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # SHA-256 of the *normalized* bytes, so two uploads of the same photo (even at
    # different original resolutions/formats) collapse to one row.
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    uploaded_by_telegram_id: Mapped[int | None] = mapped_column(BigInteger)

    # Provenance. Required for anything not photographed by staff: on a
    # NAFDAC-regulated pharmacy we must be able to answer "where did this picture of
    # a medicine come from, and on what basis was it attached to this product?"
    # Null for staff photos taken through the bot, where the answer is self-evident.
    source_url: Mapped[str | None] = mapped_column(Text)
    match_basis: Mapped[str | None] = mapped_column(Text)
