"""Track 4 — staff approval of scraped image candidates.

Approval is the ONLY route from a scraped image to products.image_id. These tests
pin that: the gate cannot be bypassed, an unmatched candidate cannot be published,
and provenance survives onto the stored asset.
"""
from __future__ import annotations

import ast
import io
from pathlib import Path

import pytest
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, ImageCandidate, MediaAsset, Product
from app.models.image_candidate import STATUS_APPROVED, STATUS_PENDING, STATUS_REJECTED
from app.services import image_candidates as svc

ROOT = Path(__file__).resolve().parent.parent


def _png(colour=(12, 200, 90), size=(120, 120)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, colour).save(buf, format="PNG")
    return buf.getvalue()


async def _seed(session: AsyncSession, *, matched: bool = True, status: str = STATUS_PENDING):
    product = Product(
        name="Emcap 500mg Caplet",
        generic_name="Ampicillin/Cloxacillin",
        brand_name="Emcap",
        manufacturer="Emzor Pharmaceutical Industries Limited",
        dosage_form="Caplet",
        strength="500 mg",
        pack_size="10*10",
        is_listed=True,
        requires_prescription=False,
        requires_review=False,
    )
    session.add(product)
    await session.flush()

    candidate = ImageCandidate(
        product_id=product.id if matched else None,
        manufacturer="Emzor Pharmaceutical Industries Limited",
        source_url="https://emzorpharma.com/emzor-products/",
        image_url="https://www.emzorpharma.com/wp-content/uploads/2019/11/02-EmCAP.png",
        scraped_title="Emcap 500mg Caplet 10*10 -image",
        scraped_strength="500mg",
        scraped_form="caplet",
        scraped_pack_size="10*10",
        match_basis="brand=emcap|strength=500mg|form=caplet|pack=10*10->100 units",
        status=status,
    )
    session.add(candidate)
    await session.flush()
    return product, candidate


# ── The queue ─────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_pending_count_counts_matched_pending_only(db_session: AsyncSession):
    await _seed(db_session)
    await _seed(db_session, matched=False)          # unmatched: excluded
    await _seed(db_session, status=STATUS_REJECTED)  # judged: excluded
    assert await svc.pending_count(db_session) == 1


@pytest.mark.asyncio
async def test_unmatched_candidates_never_enter_the_queue(db_session: AsyncSession):
    await _seed(db_session, matched=False)
    assert await svc.next_pending(db_session) is None


@pytest.mark.asyncio
async def test_queue_respects_skips(db_session: AsyncSession):
    _, c = await _seed(db_session)
    assert await svc.next_pending(db_session) is not None
    assert await svc.next_pending(db_session, skip_ids={c.id}) is None


# ── Approval publishes, and records provenance ────────────────────────────────
@pytest.mark.asyncio
async def test_approve_sets_image_id_and_marks_approved(db_session: AsyncSession):
    product, candidate = await _seed(db_session)
    assert product.image_id is None

    await svc.approve(db_session, candidate, _png(), admin_id=77)
    await db_session.flush()

    assert product.image_id is not None
    assert candidate.status == STATUS_APPROVED
    assert candidate.reviewed_by_telegram_id == 77


@pytest.mark.asyncio
async def test_provenance_persisted_on_the_media_asset(db_session: AsyncSession):
    _, candidate = await _seed(db_session)
    await svc.approve(db_session, candidate, _png(), admin_id=77)
    await db_session.flush()

    asset = (await db_session.execute(select(MediaAsset))).scalars().one()
    assert asset.source_url == candidate.image_url
    assert asset.match_basis == candidate.match_basis
    assert asset.content_type == "image/webp"          # normalized, EXIF stripped
    assert candidate.image_sha256 == asset.sha256


@pytest.mark.asyncio
async def test_approval_is_audited(db_session: AsyncSession):
    _, candidate = await _seed(db_session)
    await svc.approve(db_session, candidate, _png(), admin_id=77)
    await db_session.flush()

    log = (
        await db_session.execute(
            select(AuditLog).where(AuditLog.action == "product_image_approved")
        )
    ).scalars().one()
    assert log.actor_telegram_id == 77
    assert log.detail["pack_size_confirmed"] is True
    assert log.detail["match_basis"] == candidate.match_basis


@pytest.mark.asyncio
async def test_duplicate_image_dedupes_by_sha256(db_session: AsyncSession):
    p1, c1 = await _seed(db_session)
    p2, c2 = await _seed(db_session)
    same = _png()

    await svc.approve(db_session, c1, same, admin_id=1)
    await svc.approve(db_session, c2, same, admin_id=1)
    await db_session.flush()

    assets = (await db_session.execute(select(MediaAsset))).scalars().all()
    assert len(assets) == 1
    assert p1.image_id == p2.image_id


# ── Rejection ─────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_reject_leaves_product_image_untouched(db_session: AsyncSession):
    product, candidate = await _seed(db_session)
    await svc.reject(db_session, candidate, admin_id=5)
    await db_session.flush()

    assert product.image_id is None
    assert candidate.status == STATUS_REJECTED
    assert (await db_session.execute(select(MediaAsset))).scalars().all() == []


@pytest.mark.asyncio
async def test_rejected_candidate_leaves_the_queue(db_session: AsyncSession):
    _, candidate = await _seed(db_session)
    await svc.reject(db_session, candidate, admin_id=5)
    await db_session.flush()
    assert await svc.next_pending(db_session) is None


# ── The gate cannot be bypassed ───────────────────────────────────────────────
@pytest.mark.asyncio
async def test_cannot_approve_an_unmatched_candidate(db_session: AsyncSession):
    _, candidate = await _seed(db_session, matched=False)
    with pytest.raises(svc.CandidateNotReviewable):
        await svc.approve(db_session, candidate, _png(), admin_id=1)


@pytest.mark.asyncio
async def test_cannot_approve_twice(db_session: AsyncSession):
    _, candidate = await _seed(db_session)
    await svc.approve(db_session, candidate, _png(), admin_id=1)
    with pytest.raises(svc.CandidateNotReviewable):
        await svc.approve(db_session, candidate, _png(), admin_id=1)


@pytest.mark.asyncio
async def test_cannot_approve_a_rejected_candidate(db_session: AsyncSession):
    _, candidate = await _seed(db_session, status=STATUS_REJECTED)
    with pytest.raises(svc.CandidateNotReviewable):
        await svc.approve(db_session, candidate, _png(), admin_id=1)


# ── Two-step confirmation is structural, not cosmetic ─────────────────────────
def test_approve_callback_is_unreachable_from_the_review_screen():
    """The review keyboard must offer only 'looks right', never 'approve' directly —
    otherwise the pack-size question could be skipped with one tap."""
    src = (ROOT / "app" / "bot" / "staff" / "image_candidates.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    review_kb = next(
        n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_review_kb"
    )
    callbacks = [
        n.value for n in ast.walk(review_kb)
        if isinstance(n, ast.keyword) and n.arg == "callback_data"
    ]
    rendered = [
        "".join(v.value for v in c.values if isinstance(v, ast.Constant))
        if isinstance(c, ast.JoinedStr) else getattr(c, "value", "")
        for c in callbacks
    ]
    assert not any("imgc:approve" in r for r in rendered), (
        "the review keyboard exposes approve directly, bypassing the pack-size check"
    )
    assert any("imgc:confirm" in r for r in rendered)


def test_pack_size_question_writes_nothing():
    """confirm_pack_size only asks; it must not call approve or touch the session."""
    src = (ROOT / "app" / "bot" / "staff" / "image_candidates.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    fn = next(
        n for n in ast.walk(tree)
        if isinstance(n, ast.AsyncFunctionDef) and n.name == "confirm_pack_size"
    )
    body = ast.dump(fn)
    assert "svc.approve" not in body and "image_id" not in body


def test_storefront_icon_fallback_is_intact():
    """A product with image_id NULL must still render its dosage-form SVG icon.

    Pinned because every track in this pipeline touches product imagery, and the
    fallback silently disappearing would leave blank tiles across the shop.
    """
    for rel in (
        Path("web") / "components" / "app" / "product-card.tsx",
        Path("web") / "app" / "shop" / "[id]" / "page.tsx",
    ):
        src = (ROOT / rel).read_text(encoding="utf-8")
        assert "DrugIcon" in src, f"{rel} lost the icon fallback entirely"
        # The conditional must branch on image_url, with DrugIcon on the else side.
        assert "image_url ?" in src, f"{rel} no longer guards on image_url"
        head, _, tail = src.partition("image_url ?")
        assert "DrugIcon" in tail, f"{rel} has no DrugIcon in the image_url fallback branch"


def test_unpriced_products_never_render_as_zero_naira():
    """A product listed before staff price it must not show "₦0".

    selling_price arrives as a string, so "0.00" is truthy and a bare `!price`
    guard lets it through. Products are deliberately listed before pricing (the
    catalogue is imported, then priced), so this is the normal state for much of
    the shop — six live products were showing ₦0 because of exactly this.
    """
    for rel in (
        Path("web") / "components" / "app" / "product-card.tsx",
        Path("web") / "app" / "shop" / "[id]" / "page.tsx",
    ):
        src = (ROOT / rel).read_text(encoding="utf-8")
        assert "isPriced" in src, f"{rel} lost the unpriced guard"
        assert "Price on request" in src, f"{rel} no longer has an unpriced label"
        assert "if (!price) return" not in src, (
            f"{rel} reintroduced the truthy-string price check that renders ₦0"
        )


def test_unpriced_products_cannot_be_added_to_cart():
    """Adding a ₦0 item would put a zero-price line through checkout."""
    card = (ROOT / "web" / "components" / "app" / "product-card.tsx").read_text(encoding="utf-8")
    assert "!isPriced(p.selling_price)" in card, "card offers Add on an unpriced product"

    detail = (ROOT / "web" / "app" / "shop" / "[id]" / "page.tsx").read_text(encoding="utf-8")
    assert "isPriced(product.selling_price)" in detail, "detail page offers Add when unpriced"
    assert "!product?.selling_price ||" not in detail, (
        "detail page reintroduced the truthy-string guard in handleAdd"
    )


def test_public_product_shape_still_carries_image_url():
    """The storefront reads image_url; the serializer must keep emitting it."""
    src = (ROOT / "app" / "api" / "v1" / "catalog.py").read_text(encoding="utf-8")
    assert "image_url" in src
    ts = (ROOT / "web" / "lib" / "api" / "catalog.ts").read_text(encoding="utf-8")
    assert "image_url: string | null" in ts


def test_bot_flow_does_not_import_dev_only_scrapers():
    """scrapling/curl_cffi live in scripts/, which .railwayignore excludes."""
    src = (ROOT / "app" / "bot" / "staff" / "image_candidates.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported += [a.name.split(".")[0] for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module.split(".")[0])
    assert "scrapling" not in imported and "curl_cffi" not in imported
    assert "httpx" in imported


# ── Tier-3 candidates get a third gate ────────────────────────────────────────
def test_brand_form_candidates_route_to_a_strength_question_not_publish():
    """A candidate matched without strength must not reach approve in two taps."""
    src = (ROOT / "app" / "bot" / "staff" / "image_candidates.py").read_text(encoding="utf-8")
    assert "imgc:strength:" in src, "no strength gate exists"

    tree = ast.parse(src)
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.AsyncFunctionDef) and n.name == "confirm_pack_size")
    body = ast.dump(fn)
    # It must branch on the brand+form basis and send those to the strength step.
    assert "BASIS_BRAND_FORM" in body
    assert "imgc:strength:" in body


def test_strength_gate_writes_nothing():
    src = (ROOT / "app" / "bot" / "staff" / "image_candidates.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.AsyncFunctionDef) and n.name == "confirm_strength")
    body = ast.dump(fn)
    assert "svc.approve" not in body
    assert "image_id" not in body


def test_approval_records_whether_a_reviewer_confirmed_strength():
    src = (ROOT / "app" / "services" / "image_candidates.py").read_text(encoding="utf-8")
    assert "strength_confirmed_by_reviewer" in src


@pytest.mark.asyncio
async def test_brand_form_candidate_is_visibly_flagged(db_session: AsyncSession):
    """The reviewer must see that strength was not verified before they look."""
    from app.bot.staff.image_candidates import _review_text

    product, candidate = await _seed(db_session)
    candidate.match_basis = "brandform=ceflonac|form=tablet [STRENGTH NOT MATCHED]"
    text = _review_text(candidate, product)
    assert "strength NOT verified" in text
