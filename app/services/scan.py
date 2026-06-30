"""Scan-to-Update: barcode decode, OCR, fuzzy product match.

Flow:
  1. decode_barcode(bytes) -> barcode_value | None   (zxing-cpp)
  2. If barcode found: find_by_barcode(session, value) -> ProductIdentifier | None
  3. run_ocr(bytes) -> text | None   (Tesseract default / Cloud optional)
  4. fuzzy_candidates(session, text) -> list[Product]   (reuses search_products)
  5. link_barcode(session, product_id, barcode, admin_id) -> ProductIdentifier
  6. record_attempt(session, ...) -> ProductScanAttempt   (always recorded)
"""
from __future__ import annotations

import asyncio
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.catalog import ProductIdentifier, ProductScanAttempt
from app.services import catalog as catalog_service
from app.services.ocr import get_provider

log = get_logger("scan")


def decode_barcode(image_bytes: bytes) -> str | None:
    """Decode the first barcode found in image_bytes. Returns value or None."""
    try:
        import zxingcpp  # type: ignore[import]
        import io
        from PIL import Image  # type: ignore[import]

        image = Image.open(io.BytesIO(image_bytes))
        results = zxingcpp.read_barcodes(image)
        if results:
            return results[0].text
    except ImportError:
        log.warning("zxingcpp_unavailable", reason="zxing-cpp not installed")
    except Exception as exc:  # noqa: BLE001
        log.error("barcode_decode_failed", error=str(exc))
    return None


async def run_ocr(image_bytes: bytes) -> str:
    """Extract text from image via the configured OCR provider."""
    provider = get_provider()
    return await provider.extract_text(image_bytes)


async def find_by_barcode(session: AsyncSession, barcode_value: str) -> ProductIdentifier | None:
    return (
        await session.execute(
            select(ProductIdentifier).where(
                ProductIdentifier.identifier_type == "barcode",
                ProductIdentifier.identifier_value == barcode_value,
            )
        )
    ).scalar_one_or_none()


async def fuzzy_candidates(session: AsyncSession, text: str, limit: int = 5):
    """Fuzzy-match OCR text against product names/aliases. Returns list[Product]."""
    if not text.strip():
        return []
    results = await catalog_service.search_products(session, text.strip()[:80])
    return results[:limit]


async def link_barcode(
    session: AsyncSession,
    product_id: UUID,
    barcode_value: str,
    admin_id: int,
    confidence_score: float | None = None,
    source: str = "scan",
) -> ProductIdentifier:
    """Create or return existing barcode -> product link."""
    existing = await find_by_barcode(session, barcode_value)
    if existing is not None:
        return existing
    ident = ProductIdentifier(
        product_id=product_id,
        identifier_type="barcode",
        identifier_value=barcode_value,
        source=source,
        confidence_score=confidence_score,
        created_by_admin_id=admin_id,
    )
    session.add(ident)
    return ident


async def record_attempt(
    session: AsyncSession,
    admin_id: int,
    image_file_id: str,
    detected_barcode: str | None = None,
    extracted_text: str | None = None,
    matched_product_ids: list[str] | None = None,
    selected_product_id: UUID | None = None,
    confidence_score: float | None = None,
    status: str = "pending",
) -> ProductScanAttempt:
    attempt = ProductScanAttempt(
        admin_id=admin_id,
        image_file_id=image_file_id,
        detected_barcode=detected_barcode,
        extracted_text=extracted_text,
        matched_product_ids=matched_product_ids,
        selected_product_id=selected_product_id,
        confidence_score=confidence_score,
        status=status,
    )
    session.add(attempt)
    return attempt
