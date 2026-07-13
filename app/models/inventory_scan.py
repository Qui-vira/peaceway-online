"""AI photo inventory intake: scan sessions, uploaded images, and detected items.

A staff member photographs shelves/products, the vision provider proposes an
inventory update, a human reviews/corrects it in Telegram, and only then is the
real catalog touched (through services.products_admin, so PriceHistory and
audit logs stay consistent). Sessions are DB-backed so a bot restart does not
lose an in-progress scan.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import JSONB, Base, TimestampMixin

# Session lifecycle (application-validated strings, same lightweight pattern as
# Prescription.review_status - adding a status never needs a column migration).
SCAN_STATUS_COLLECTING = "collecting_images"
SCAN_STATUS_ANALYSING = "analysing"
SCAN_STATUS_REVIEW = "awaiting_review"
SCAN_STATUS_COMMITTED = "committed"
SCAN_STATUS_CANCELLED = "cancelled"
SCAN_STATUS_FAILED = "failed"

# Scan modes - how confirmed quantities are applied to the catalog.
SCAN_MODE_SET = "set_stock"      # full stock count: detected qty replaces stock
SCAN_MODE_ADD = "add_stock"      # new stock received: detected qty adds to stock
SCAN_MODE_DRAFT = "draft"        # reviewable draft only, no stock changes

SCAN_MODES = (SCAN_MODE_SET, SCAN_MODE_ADD, SCAN_MODE_DRAFT)

# Item match classification against the existing catalog.
MATCH_EXACT = "exact_existing"
MATCH_PROBABLE = "probable_existing"
MATCH_NEW = "new_product"
MATCH_UNCERTAIN = "uncertain"

# Proposed per-item action.
ACTION_SET_STOCK = "set_stock"
ACTION_ADD_STOCK = "add_stock"
ACTION_CREATE = "create_product"
ACTION_NO_CHANGE = "no_change"
ACTION_REVIEW = "needs_review"
ACTION_DRAFT = "draft"

# Human review state per item.
REVIEW_PENDING = "pending"
REVIEW_CONFIRMED = "confirmed"
REVIEW_EDITED = "edited"
REVIEW_SKIPPED = "skipped"


class InventoryScanSession(Base, TimestampMixin):
    """One photo-scan workflow run by one staff member."""

    __tablename__ = "inventory_scan_sessions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    admin_telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    scan_mode: Mapped[str] = mapped_column(String(20), default=SCAN_MODE_SET, nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), default=SCAN_STATUS_COLLECTING, nullable=False, index=True
    )
    warnings: Mapped[list | None] = mapped_column(JSONB)
    error: Mapped[str | None] = mapped_column(Text)
    analysis_summary: Mapped[dict | None] = mapped_column(JSONB)
    commit_summary: Mapped[dict | None] = mapped_column(JSONB)
    committed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    images: Mapped[list["InventoryScanImage"]] = relationship(
        back_populates="scan_session",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="InventoryScanImage.position",
    )
    items: Mapped[list["InventoryScanItem"]] = relationship(
        back_populates="scan_session",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="InventoryScanItem.item_index",
    )


class InventoryScanImage(Base, TimestampMixin):
    """One uploaded photo in a scan session (referenced by Telegram file id)."""

    __tablename__ = "inventory_scan_images"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("inventory_scan_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    telegram_file_id: Mapped[str] = mapped_column(String(255), nullable=False)
    # Telegram's stable per-file id - used to reject duplicate uploads.
    file_unique_id: Mapped[str] = mapped_column(String(128), nullable=False)
    media_group_id: Mapped[str | None] = mapped_column(String(64))
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), default="received", nullable=False)  # received|analysed|unreadable

    scan_session: Mapped[InventoryScanSession] = relationship(back_populates="images")

    __table_args__ = (
        UniqueConstraint("session_id", "file_unique_id", name="uq_scan_image_per_session"),
    )


class InventoryScanItem(Base, TimestampMixin):
    """One distinct product the AI detected across the photo batch."""

    __tablename__ = "inventory_scan_items"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("inventory_scan_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    item_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Normalized candidate fields (CSV-importer vocabulary).
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100))
    dosage: Mapped[str | None] = mapped_column(String(100))
    prescription: Mapped[str] = mapped_column(String(20), default="uncertain", nullable=False)  # OTC|Rx|uncertain
    availability: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000))
    cost_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    selling_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    detected_stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    counting_notes: Mapped[str | None] = mapped_column(Text)
    source_images: Mapped[list | None] = mapped_column(JSONB)  # positions into session images

    # Separate confidence axes (see spec: no single fake number).
    identity_confidence: Mapped[float | None] = mapped_column(Float)
    stock_count_confidence: Mapped[float | None] = mapped_column(Float)
    match_confidence: Mapped[float | None] = mapped_column(Float)

    match_type: Mapped[str] = mapped_column(String(30), default=MATCH_UNCERTAIN, nullable=False)
    matched_product_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL")
    )
    proposed_action: Mapped[str] = mapped_column(String(30), default=ACTION_REVIEW, nullable=False)
    review_status: Mapped[str] = mapped_column(String(20), default=REVIEW_PENDING, nullable=False)
    # Every human correction: [{field, old, new, admin_id, at}]
    corrections: Mapped[list | None] = mapped_column(JSONB)
    committed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    scan_session: Mapped[InventoryScanSession] = relationship(back_populates="items")
