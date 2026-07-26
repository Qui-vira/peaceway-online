"""Scraped manufacturer images awaiting staff approval.

This table is a quarantine. The scraper writes here and ONLY here — nothing in the
pipeline may set products.image_id. A candidate becomes a real product image only
when a staff member approves it in Telegram, because a photo showing a different
pack, strength or manufacturer than what is dispensed is a patient-safety failure,
not a cosmetic one.

Lives under app/models (not scripts/) because the staff approval flow in
app/bot/staff/ needs it, and .railwayignore keeps scripts/ out of the deployed
container.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

STATUS_PENDING = "pending"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"
STATUSES = (STATUS_PENDING, STATUS_APPROVED, STATUS_REJECTED)


class ImageCandidate(Base, TimestampMixin):
    """One manufacturer image, optionally paired with one product."""

    __tablename__ = "image_candidates"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # Null when the scraped item matched no product. Those rows are kept
    # deliberately: they are the coverage gap, and deleting them would hide it.
    product_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )

    manufacturer: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[str] = mapped_column(Text, nullable=False)

    # Exactly what the manufacturer's page said, before any normalization.
    scraped_title: Mapped[str] = mapped_column(String(500), nullable=False)
    scraped_strength: Mapped[str | None] = mapped_column(String(100))
    scraped_form: Mapped[str | None] = mapped_column(String(100))
    scraped_pack_size: Mapped[str | None] = mapped_column(String(100))

    # Set once the image bytes are fetched, so a re-scrape can skip known images and
    # approval can dedupe against media_assets.
    image_sha256: Mapped[str | None] = mapped_column(String(64), index=True)

    # The literal comparison that succeeded, plus any normalization applied, e.g.
    # "brand=Emcap|strength=500mg|form=caplet|pack=10*10->100 units"
    match_basis: Mapped[str | None] = mapped_column(Text)

    status: Mapped[str] = mapped_column(String(20), default=STATUS_PENDING, nullable=False, index=True)
    reviewed_by_telegram_id: Mapped[int | None] = mapped_column(BigInteger)
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        # Re-running the scraper updates rather than duplicating.
        UniqueConstraint("product_id", "image_url", name="uq_image_candidate_product_image"),
    )
