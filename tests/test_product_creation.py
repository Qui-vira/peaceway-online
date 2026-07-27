"""Creating catalogue entries from crawled manufacturer products.

A created product is a DRAFT: never listed, never priced, always flagged for
pharmacist review. And a duplicate medicine record is worse than a missing one, so
the duplicate guards matter as much as the creation itself.
"""
from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, Product, ProductPricing
from app.services.image_matching import ScrapedItem
from app.services.product_creation import create_from_scraped, find_duplicate

MFR = "Geneith Pharmaceuticals Limited"


def _item(**over) -> ScrapedItem:
    d = dict(
        manufacturer=MFR,
        source_url="https://www.geneithpharm.com/product-category/anti-malarials",
        image_url="https://www.geneithpharm.com/x/Camosunate.png",
        title="Camosunate Adult Tablets",
        brand="Camosunate Adult",
        strength="100 mg",
        form="tablet",
        pack_size="6",
        nafdac="A4-1234",
    )
    d.update(over)
    return ScrapedItem(**d)


async def _existing(session: AsyncSession, **over) -> Product:
    d = dict(
        name="Camosunate Adult Tablets", generic_name="Artesunate/Amodiaquine",
        brand_name="Camosunate Adult", manufacturer=MFR, dosage_form="Tablet",
        strength="100 mg", nafdac_number="A4-1234",
        is_listed=True, requires_prescription=False, requires_review=False,
    )
    d.update(over)
    p = Product(**d)
    session.add(p)
    await session.flush()
    return p


# ── A created product is a draft, never a purchasable item ────────────────────
@pytest.mark.asyncio
async def test_created_product_is_never_listed(db_session: AsyncSession):
    p = await create_from_scraped(db_session, _item())
    assert p.is_listed is False


@pytest.mark.asyncio
async def test_created_product_is_flagged_for_review(db_session: AsyncSession):
    """It was assembled from a web page, not checked by a pharmacist."""
    p = await create_from_scraped(db_session, _item())
    assert p.requires_review is True


@pytest.mark.asyncio
async def test_created_product_has_no_price(db_session: AsyncSession):
    p = await create_from_scraped(db_session, _item())
    await db_session.flush()
    pricing = (
        await db_session.execute(select(ProductPricing).where(ProductPricing.product_id == p.id))
    ).scalars().one()
    assert not pricing.selling_price
    assert pricing.is_in_stock is False


@pytest.mark.asyncio
async def test_created_product_copies_only_published_fields(db_session: AsyncSession):
    p = await create_from_scraped(db_session, _item(strength=None, form=None))
    assert p.strength is None and p.dosage_form is None
    assert p.brand_name == "Camosunate Adult"


@pytest.mark.asyncio
async def test_creation_is_audited(db_session: AsyncSession):
    await create_from_scraped(db_session, _item(), admin_id=9)
    await db_session.flush()
    log = (
        await db_session.execute(
            select(AuditLog).where(AuditLog.action == "product_created_from_manufacturer_site")
        )
    ).scalars().one()
    assert log.detail["created_unlisted_and_unpriced"] is True
    assert log.detail["manufacturer"] == MFR


@pytest.mark.asyncio
async def test_item_with_no_name_is_refused(db_session: AsyncSession):
    with pytest.raises(ValueError):
        await create_from_scraped(db_session, _item(title="", brand=None))


# ── Duplicate guards ──────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_duplicate_by_nafdac_number(db_session: AsyncSession):
    await _existing(db_session)
    dup = await find_duplicate(db_session, _item(title="Totally Different Name"))
    assert dup is not None and "NAFDAC" in dup.reason


@pytest.mark.asyncio
async def test_duplicate_by_brand_form_strength(db_session: AsyncSession):
    await _existing(db_session, nafdac_number=None)
    dup = await find_duplicate(db_session, _item(nafdac=None, title="Another Name"))
    assert dup is not None and "brand + form + strength" in dup.reason


@pytest.mark.asyncio
async def test_duplicate_by_name(db_session: AsyncSession):
    await _existing(db_session, nafdac_number=None, brand_name=None)
    dup = await find_duplicate(db_session, _item(nafdac=None, brand=None))
    assert dup is not None and "same name" in dup.reason


@pytest.mark.asyncio
async def test_genuinely_new_product_is_not_a_duplicate(db_session: AsyncSession):
    await _existing(db_session)
    dup = await find_duplicate(
        db_session, _item(nafdac="B9-9999", brand="Coatal Forte", title="Coatal Forte Tablets")
    )
    assert dup is None


@pytest.mark.asyncio
async def test_same_brand_different_strength_is_not_a_duplicate(db_session: AsyncSession):
    """Two strengths of one brand are different products, not duplicates."""
    await _existing(db_session, nafdac_number=None)
    dup = await find_duplicate(db_session, _item(nafdac=None, strength="200 mg",
                                                 title="Camosunate Adult 200"))
    assert dup is None


@pytest.mark.asyncio
async def test_duplicate_check_is_scoped_to_the_manufacturer(db_session: AsyncSession):
    """Another company's identically-named product is a different medicine."""
    await _existing(db_session, manufacturer="Emzor Pharmaceutical Industries Limited",
                    nafdac_number=None)
    dup = await find_duplicate(db_session, _item(nafdac=None))
    assert dup is None


@pytest.mark.asyncio
async def test_blank_brand_does_not_collapse_into_a_false_duplicate(db_session: AsyncSession):
    """Two products both missing a brand must not look like the same product."""
    await _existing(db_session, nafdac_number=None, brand_name=None, name="Something Else")
    dup = await find_duplicate(db_session, _item(nafdac=None, brand=None, title="Different Again"))
    assert dup is None
