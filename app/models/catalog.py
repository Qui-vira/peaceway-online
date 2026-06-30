"""Product catalog models — imported/normalized from PharmaOS, priced by Peaceway."""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import JSONB, Base, TimestampMixin


class Product(Base, TimestampMixin):
    """Global product, normalized from PharmaOS. Pricing/stock live in ProductPricing."""

    __tablename__ = "products"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    generic_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    brand_name: Mapped[str | None] = mapped_column(String(255))
    dosage_form: Mapped[str | None] = mapped_column(String(100))
    strength: Mapped[str | None] = mapped_column(String(100))
    manufacturer: Mapped[str | None] = mapped_column(String(255))
    nafdac_number: Mapped[str | None] = mapped_column(String(100), unique=True, index=True)
    category: Mapped[str | None] = mapped_column(String(100), index=True)

    description: Mapped[str | None] = mapped_column(String(1000))
    requires_prescription: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    controlled_substance: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Anything not explicitly cleared by a pharmacist needs review before sale.
    requires_review: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Only listed products are shown as buyable to customers.
    is_listed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    aliases: Mapped[list["ProductAlias"]] = relationship(
        back_populates="product", cascade="all, delete-orphan", lazy="selectin"
    )
    pricing: Mapped["ProductPricing | None"] = relationship(
        back_populates="product", cascade="all, delete-orphan", uselist=False, lazy="selectin"
    )

    __table_args__ = (Index("ix_products_generic_strength", "generic_name", "strength"),)


class ProductAlias(Base, TimestampMixin):
    """Variant drug names mapped to a canonical product (e.g. 'PCM 500' -> Paracetamol)."""

    __tablename__ = "product_aliases"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    alias_name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    product: Mapped[Product] = relationship(back_populates="aliases")

    __table_args__ = (UniqueConstraint("alias_name", name="uq_alias_name"),)


class ProductPricing(Base, TimestampMixin):
    """Peaceway's own cost/selling price and stock for a product."""

    __tablename__ = "product_pricing"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    cost_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    selling_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    # Optional pricing controls — admin sets one of these to derive selling_price.
    markup_pct: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    fixed_profit: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    stock_qty: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_in_stock: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    product: Mapped[Product] = relationship(back_populates="pricing")


class PriceHistory(Base, TimestampMixin):
    """Audit trail of every price/stock change, for the 'View Price History' view."""

    __tablename__ = "price_history"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    field: Mapped[str] = mapped_column(String(40), nullable=False)  # selling_price|cost_price|stock|category|...
    old_value: Mapped[str | None] = mapped_column(String(255))
    new_value: Mapped[str | None] = mapped_column(String(255))
    changed_by: Mapped[int | None] = mapped_column(BigInteger)  # admin telegram_id
    reason: Mapped[str | None] = mapped_column(Text)


class ProductIdentifier(Base, TimestampMixin):
    """Barcode/SKU/alias mappings that let a scan resolve to a product."""

    __tablename__ = "product_identifiers"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    identifier_type: Mapped[str] = mapped_column(String(20), nullable=False)  # barcode|sku|ocr_alias|manual_code
    identifier_value: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False)  # scan|manual|csv
    confidence_score: Mapped[float | None] = mapped_column(Float)
    created_by_admin_id: Mapped[int | None] = mapped_column(BigInteger)

    __table_args__ = (
        UniqueConstraint("identifier_type", "identifier_value", name="uq_product_identifier"),
    )


class ProductScanAttempt(Base, TimestampMixin):
    """Full audit trail of every admin scan attempt, matched or not."""

    __tablename__ = "product_scan_attempts"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    admin_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    image_file_id: Mapped[str] = mapped_column(String(255), nullable=False)
    detected_barcode: Mapped[str | None] = mapped_column(String(255))
    extracted_text: Mapped[str | None] = mapped_column(Text)
    matched_product_ids: Mapped[list | None] = mapped_column(JSONB)
    selected_product_id: Mapped[UUID | None] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"))
    confidence_score: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)  # pending|matched|unmatched|linked|failed
