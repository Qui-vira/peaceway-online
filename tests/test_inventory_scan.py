"""AI photo inventory intake: session lifecycle, validation, dedup, matching,
review corrections, CSV export, safe commit, and audit trail.

Provider calls are never made here — the pipeline is exercised with validated
InventoryScanResult fixtures, exactly as the bot does after parse_scan_result.
"""
from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core import rbac
from app.models import AuditLog, PriceHistory, Product, ProductPricing
from app.models.inventory_scan import (
    ACTION_ADD_STOCK,
    ACTION_CREATE,
    ACTION_REVIEW,
    ACTION_SET_STOCK,
    MATCH_EXACT,
    MATCH_NEW,
    MATCH_PROBABLE,
    REVIEW_CONFIRMED,
    REVIEW_PENDING,
    REVIEW_SKIPPED,
    SCAN_MODE_ADD,
    SCAN_MODE_DRAFT,
    SCAN_MODE_SET,
    SCAN_STATUS_COLLECTING,
    SCAN_STATUS_COMMITTED,
    SCAN_STATUS_REVIEW,
)
from app.services import inventory_scan as svc
from app.services.inventory_vision.base import VisionResultError
from app.services.inventory_vision.schemas import (
    DetectedProduct,
    InventoryScanResult,
    parse_scan_result,
)

ADMIN = 777
CHAT = 888


def _detected(name="Relcer Gel", stock=1, dosage=None, category="Medicines",
              identity=0.95, count_conf=0.92, prescription="OTC",
              source_images=None, notes="counted") -> DetectedProduct:
    return DetectedProduct(
        temporary_id=f"scan_item_{uuid4().hex[:6]}",
        product_name=name,
        category=category,
        stock=stock,
        dosage=dosage,
        prescription=prescription,
        description=None,
        identity_confidence=identity,
        stock_count_confidence=count_conf,
        source_images=source_images or [0],
        counting_notes=notes,
    )


async def _make_scan(session, mode=SCAN_MODE_SET, images=1):
    scan = await svc.create_scan_session(session, ADMIN, CHAT, mode)
    for i in range(images):
        await svc.add_image(session, scan, f"file{i}", f"uniq{i}")
    return scan


async def _make_product(session, name="Relcer Gel", stock=4, price="1500",
                        strength=None) -> Product:
    p = Product(name=name, generic_name=name, strength=strength)
    session.add(p)
    await session.flush()
    session.add(ProductPricing(
        product_id=p.id, stock_qty=stock,
        selling_price=Decimal(price), is_in_stock=stock > 0,
    ))
    await session.flush()
    return p


# ── 1+2. Access control ──────────────────────────────────────────────────────

def test_authorized_roles_can_scan_inventory():
    assert rbac.has_permission({rbac.LEAD_PHARMACIST}, "scan_inventory")
    assert rbac.has_permission({rbac.SYSTEM_OWNER}, "scan_inventory")  # via wildcard


def test_unauthorized_roles_cannot_scan_inventory():
    for role in (rbac.SALES_SUPPORT, rbac.PACKAGING, rbac.DISPATCHER,
                 rbac.FINANCE, rbac.COMMUNITY_MANAGER, rbac.PHARMACIST_ADMIN):
        assert not rbac.has_permission({role}, "scan_inventory"), role
    assert not rbac.has_permission(set(), "scan_inventory")


# ── 3+4. Batch collection: photos attach, analysis waits for the button ─────

@pytest.mark.asyncio
async def test_multiple_photos_attach_to_one_session(session):
    scan = await _make_scan(session, images=0)
    for i in range(4):
        img, total = await svc.add_image(session, scan, f"f{i}", f"u{i}", media_group_id="alb1")
        assert img is not None
        assert total == i + 1
    await session.refresh(scan, ["images"])
    assert len(scan.images) == 4
    assert [img.position for img in scan.images] == [0, 1, 2, 3]


@pytest.mark.asyncio
async def test_duplicate_photo_is_not_added_twice(session):
    scan = await _make_scan(session, images=0)
    await svc.add_image(session, scan, "fA", "same-unique-id")
    dup, total = await svc.add_image(session, scan, "fB", "same-unique-id")
    assert dup is None
    assert total == 1


@pytest.mark.asyncio
async def test_collecting_photos_does_not_trigger_analysis(session):
    """The workflow waits for the explicit Analyse action."""
    scan = await _make_scan(session, images=3)
    assert scan.status == SCAN_STATUS_COLLECTING
    await session.refresh(scan, ["items"])
    assert scan.items == []


# ── 5+6. Structured result validation ────────────────────────────────────────

def test_valid_ai_result_is_parsed():
    raw = {
        "products": [{
            "temporary_id": "scan_item_001",
            "product_name": "Relcer Gel",
            "category": "Medicines",
            "stock": 1,
            "dosage": None,
            "prescription": "OTC",
            "description": "Antacid gel",
            "identity_confidence": 0.97,
            "stock_count_confidence": 0.92,
            "source_images": [0, 1],
            "counting_notes": "1 visible box.",
        }],
        "warnings": [],
        "unreadable_images": [],
    }
    result = parse_scan_result(raw)
    assert result.products[0].product_name == "Relcer Gel"
    assert result.products[0].stock == 1


def test_invalid_ai_results_are_rejected():
    with pytest.raises(VisionResultError):
        parse_scan_result("{not json")
    with pytest.raises(VisionResultError):
        parse_scan_result('["a list, not an object"]')
    # Invented category
    bad_cat = {"products": [{
        "temporary_id": "x", "product_name": "Thing", "category": "Cosmetics",
        "stock": 1, "dosage": None, "prescription": "OTC", "description": None,
        "identity_confidence": 0.9, "stock_count_confidence": 0.9,
        "source_images": [], "counting_notes": "",
    }], "warnings": [], "unreadable_images": []}
    with pytest.raises(VisionResultError):
        parse_scan_result(bad_cat)
    # Negative stock
    bad_stock = {**bad_cat}
    bad_stock["products"] = [{**bad_cat["products"][0], "category": "Medicines", "stock": -2}]
    with pytest.raises(VisionResultError):
        parse_scan_result(bad_stock)
    # Blank product name
    bad_name = {**bad_cat}
    bad_name["products"] = [{**bad_cat["products"][0], "category": "Medicines", "product_name": "  "}]
    with pytest.raises(VisionResultError):
        parse_scan_result(bad_name)


# ── 7+8. Counting: same SKU multiple units, no overlap double-count ─────────

def test_same_sku_multiple_units_keep_their_count():
    merged, notes = svc.merge_duplicate_candidates([_detected(stock=8)])
    assert merged[0].stock == 8
    assert notes == []


def test_duplicate_detections_take_max_not_sum():
    """Two detections of the same product from overlapping photos must not add."""
    merged, notes = svc.merge_duplicate_candidates([
        _detected(name="Relcer Gel", stock=5, source_images=[0]),
        _detected(name="RELCER GEL", stock=3, source_images=[1]),
    ])
    assert len(merged) == 1
    assert merged[0].stock == 5  # max, never 8
    assert merged[0].source_images == [0, 1]
    assert notes


def test_different_dosages_are_never_merged():
    merged, _ = svc.merge_duplicate_candidates([
        _detected(name="Amoxil", dosage="250mg", stock=2),
        _detected(name="Amoxil", dosage="500mg", stock=3),
    ])
    assert len(merged) == 2  # possibly different SKUs


# ── 9+10. Database matching ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_existing_product_matches_despite_case_and_spacing(session):
    p = await _make_product(session, "Relcer Gel")
    match_type, product, conf = await svc.match_candidate(session, "RELCER  GEL", None)
    assert match_type == MATCH_EXACT
    assert product.id == p.id
    assert conf >= 0.9


@pytest.mark.asyncio
async def test_dosage_mismatch_is_not_auto_merged(session):
    await _make_product(session, "Amoxil", strength="250mg")
    match_type, product, _ = await svc.match_candidate(session, "Amoxil", "500mg")
    assert match_type == MATCH_PROBABLE  # human must decide — may be a new SKU
    assert product is not None


@pytest.mark.asyncio
async def test_unknown_product_is_new(session):
    match_type, product, _ = await svc.match_candidate(session, "Danacid", None)
    assert match_type == MATCH_NEW
    assert product is None


# ── 11. Confidence and escalation ────────────────────────────────────────────

def test_low_confidence_requires_review():
    assert svc.plan_action(MATCH_EXACT, 0.4, 0.9, SCAN_MODE_SET) == ACTION_REVIEW
    assert svc.plan_action(MATCH_NEW, 0.9, 0.3, SCAN_MODE_SET) == ACTION_REVIEW
    assert svc.plan_action(MATCH_PROBABLE, 0.9, 0.9, SCAN_MODE_SET) == ACTION_REVIEW


def test_high_confidence_actions_follow_scan_mode():
    assert svc.plan_action(MATCH_EXACT, 0.95, 0.95, SCAN_MODE_SET) == ACTION_SET_STOCK
    assert svc.plan_action(MATCH_EXACT, 0.95, 0.95, SCAN_MODE_ADD) == ACTION_ADD_STOCK
    assert svc.plan_action(MATCH_NEW, 0.95, 0.95, SCAN_MODE_SET) == ACTION_CREATE


@pytest.mark.asyncio
async def test_bulk_confirm_skips_low_confidence_items(session):
    await _make_product(session, "Relcer Gel")
    scan = await _make_scan(session)
    result = InventoryScanResult(products=[
        _detected(name="Relcer Gel", stock=2),                       # high conf, exact
        _detected(name="Blurrymed", stock=1, identity=0.3, count_conf=0.4),  # low conf
    ])
    await svc.run_analysis(session, scan, result)
    confirmed = svc.confirm_safe_items(scan)
    assert confirmed == 1
    by_name = {i.product_name: i for i in scan.items}
    assert by_name["Relcer Gel"].review_status == REVIEW_CONFIRMED
    assert by_name["Blurrymed"].review_status == REVIEW_PENDING
    assert by_name["Blurrymed"].proposed_action == ACTION_REVIEW


# ── 12. Human corrections ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_human_can_edit_stock_with_full_audit(session):
    scan = await _make_scan(session)
    await svc.run_analysis(session, scan, InventoryScanResult(products=[_detected(stock=8)]))
    item = scan.items[0]

    await svc.apply_correction(session, item, "stock", "5", ADMIN, scan.scan_mode)

    assert item.detected_stock == 5
    assert item.review_status == "edited"
    corr = item.corrections[0]
    assert corr["field"] == "stock"
    assert corr["old"] == "8"          # original AI value preserved
    assert corr["new"] == "5"
    assert corr["admin_id"] == ADMIN
    assert corr["at"]                  # timestamp recorded


@pytest.mark.asyncio
async def test_invalid_edit_is_rejected(session):
    scan = await _make_scan(session)
    await svc.run_analysis(session, scan, InventoryScanResult(products=[_detected()]))
    item = scan.items[0]
    with pytest.raises(ValueError):
        await svc.apply_correction(session, item, "stock", "many", ADMIN, scan.scan_mode)
    with pytest.raises(ValueError):
        await svc.apply_correction(session, item, "category", "Cosmetics", ADMIN, scan.scan_mode)
    with pytest.raises(ValueError):
        await svc.apply_correction(session, item, "nafdac_number", "x", ADMIN, scan.scan_mode)


# ── 13+14. CSV export ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_csv_has_exact_header_and_reviewed_quantities(session):
    scan = await _make_scan(session)
    await svc.run_analysis(session, scan, InventoryScanResult(products=[
        _detected(name="Relcer Gel", stock=8),
        _detected(name="Danacid", stock=4, dosage="250mg"),
        _detected(name="Skipped Thing", stock=9),
    ]))
    items = {i.product_name: i for i in scan.items}
    await svc.apply_correction(session, items["Relcer Gel"], "stock", "5", ADMIN, scan.scan_mode)
    items["Skipped Thing"].review_status = REVIEW_SKIPPED

    csv_text = svc.generate_csv(scan)
    lines = csv_text.strip().split("\n")
    assert lines[0] == "product_name,category,cost_price,selling_price,stock,dosage,prescription,availability,description"
    assert any(line.startswith("Relcer Gel,") and ",5," in line for line in lines[1:])
    assert any(line.startswith("Danacid,") and ",4," in line and "250mg" in line for line in lines[1:])
    assert not any("Skipped Thing" in line for line in lines)
    # cost/selling price stay blank when unknown
    relcer = next(line for line in lines[1:] if line.startswith("Relcer Gel,"))
    assert relcer.split(",")[2] == "" and relcer.split(",")[3] == ""


# ── 15. Nothing changes before confirmation ──────────────────────────────────

@pytest.mark.asyncio
async def test_no_inventory_change_before_commit(session):
    product = await _make_product(session, "Relcer Gel", stock=4)
    scan = await _make_scan(session)
    await svc.run_analysis(session, scan, InventoryScanResult(products=[
        _detected(name="Relcer Gel", stock=1),
        _detected(name="Danacid", stock=4),
    ]))
    assert scan.status == SCAN_STATUS_REVIEW

    pricing = (await session.execute(
        select(ProductPricing).where(ProductPricing.product_id == product.id)
    )).scalar_one()
    assert pricing.stock_qty == 4  # untouched
    names = (await session.execute(select(Product.name))).scalars().all()
    assert "Danacid" not in names  # no product created yet


# ── 16+17. Commit + audit trail ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_commit_sets_stock_creates_products_and_audits(session):
    product = await _make_product(session, "Relcer Gel", stock=4)
    scan = await _make_scan(session, mode=SCAN_MODE_SET)
    await svc.run_analysis(session, scan, InventoryScanResult(products=[
        _detected(name="Relcer Gel", stock=1),
        _detected(name="Danacid", stock=4, dosage="250mg", prescription="OTC"),
        _detected(name="Left Out", stock=2),
    ]))
    for item in scan.items:
        if item.product_name != "Left Out":
            item.review_status = REVIEW_CONFIRMED

    summary = await svc.commit_scan_session(session, scan, ADMIN)

    assert summary == {**summary, "updated": 1, "created": 1, "skipped": 1}
    assert scan.status == SCAN_STATUS_COMMITTED
    pricing = (await session.execute(
        select(ProductPricing).where(ProductPricing.product_id == product.id)
    )).scalar_one()
    assert pricing.stock_qty == 1  # SET mode replaced 4 -> 1

    danacid = (await session.execute(
        select(Product).where(Product.name == "Danacid")
    )).scalar_one()
    assert danacid.strength == "250mg"
    assert danacid.requires_prescription is False

    # Unreviewed item was NOT committed.
    assert (await session.execute(
        select(Product).where(Product.name == "Left Out")
    )).scalar_one_or_none() is None

    # Price history recorded through the shared products_admin path.
    history = (await session.execute(
        select(PriceHistory).where(PriceHistory.product_id == product.id,
                                   PriceHistory.field == "stock")
    )).scalars().all()
    assert any(h.new_value == "1" and h.changed_by == ADMIN for h in history)

    # Scan-level audit log.
    audit = (await session.execute(
        select(AuditLog).where(AuditLog.action == "inventory_scan_commit")
    )).scalar_one()
    assert audit.entity_id == str(scan.id)
    assert audit.detail["updated"] == 1 and audit.detail["created"] == 1
    assert audit.detail["scan_mode"] == SCAN_MODE_SET


@pytest.mark.asyncio
async def test_commit_add_mode_adds_to_existing_stock(session):
    product = await _make_product(session, "Relcer Gel", stock=4)
    scan = await _make_scan(session, mode=SCAN_MODE_ADD)
    await svc.run_analysis(session, scan, InventoryScanResult(products=[
        _detected(name="Relcer Gel", stock=3),
    ]))
    scan.items[0].review_status = REVIEW_CONFIRMED
    await svc.commit_scan_session(session, scan, ADMIN)
    pricing = (await session.execute(
        select(ProductPricing).where(ProductPricing.product_id == product.id)
    )).scalar_one()
    assert pricing.stock_qty == 7  # 4 + 3


@pytest.mark.asyncio
async def test_draft_mode_commit_changes_nothing(session):
    product = await _make_product(session, "Relcer Gel", stock=4)
    scan = await _make_scan(session, mode=SCAN_MODE_DRAFT)
    await svc.run_analysis(session, scan, InventoryScanResult(products=[
        _detected(name="Relcer Gel", stock=1),
        _detected(name="Danacid", stock=4),
    ]))
    for item in scan.items:
        item.review_status = REVIEW_CONFIRMED
    summary = await svc.commit_scan_session(session, scan, ADMIN)
    assert summary["drafted"] == 2 and summary["updated"] == 0 and summary["created"] == 0
    pricing = (await session.execute(
        select(ProductPricing).where(ProductPricing.product_id == product.id)
    )).scalar_one()
    assert pricing.stock_qty == 4
    assert (await session.execute(
        select(Product).where(Product.name == "Danacid")
    )).scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_uncertain_prescription_new_product_stays_review_required(session):
    """Pharmacy safety: never invent Rx status — product waits for a pharmacist."""
    scan = await _make_scan(session, mode=SCAN_MODE_SET)
    await svc.run_analysis(session, scan, InventoryScanResult(products=[
        _detected(name="Mysterysyrup", stock=2, prescription="uncertain"),
    ]))
    scan.items[0].review_status = REVIEW_CONFIRMED
    await svc.commit_scan_session(session, scan, ADMIN)
    p = (await session.execute(
        select(Product).where(Product.name == "Mysterysyrup")
    )).scalar_one()
    assert p.requires_review is True  # not sellable until cleared


# ── 18. Failed commit leaves no partial state ────────────────────────────────

@pytest.mark.asyncio
async def test_failed_commit_rolls_back_cleanly(session):
    product = await _make_product(session, "Relcer Gel", stock=4)
    product_id = product.id  # captured before rollback expires the instance
    scan = await _make_scan(session, mode=SCAN_MODE_SET)
    await svc.run_analysis(session, scan, InventoryScanResult(products=[
        _detected(name="Relcer Gel", stock=1),
        _detected(name="Ghost Product", stock=2),
    ]))
    for item in scan.items:
        item.review_status = REVIEW_CONFIRMED
    # Sabotage the second item: its match points at a product that no longer exists.
    ghost = next(i for i in scan.items if i.product_name == "Ghost Product")
    ghost.matched_product_id = uuid4()
    await session.flush()

    # Production wraps the commit in one transaction (get_session rolls back on
    # error); a SAVEPOINT models that here without discarding the test setup.
    with pytest.raises(ValueError):
        async with session.begin_nested():
            await svc.commit_scan_session(session, scan, ADMIN)

    pricing = (await session.execute(
        select(ProductPricing).where(ProductPricing.product_id == product_id)
    )).scalar_one()
    assert pricing.stock_qty == 4  # first item's update was rolled back too
    audit = (await session.execute(
        select(AuditLog).where(AuditLog.action == "inventory_scan_commit")
    )).scalar_one_or_none()
    assert audit is None


# ── Session lifecycle extras ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_active_session_lookup_and_cancel(session):
    scan = await _make_scan(session)
    found = await svc.get_active_session(session, ADMIN)
    assert found is not None and found.id == scan.id
    await svc.cancel_scan(session, scan)
    assert await svc.get_active_session(session, ADMIN) is None


@pytest.mark.asyncio
async def test_rematch_item_to_existing_product(session):
    target = await _make_product(session, "Relcer Gel Original", stock=4)
    scan = await _make_scan(session)
    await svc.run_analysis(session, scan, InventoryScanResult(products=[
        _detected(name="Relcer antacid gel", stock=2, identity=0.7),
    ]))
    item = scan.items[0]
    await svc.set_item_match(session, item, target, ADMIN, scan.scan_mode)
    assert item.matched_product_id == target.id
    assert item.match_type == MATCH_EXACT
    assert item.proposed_action == ACTION_SET_STOCK
    assert item.corrections[-1]["field"] == "matched_product_id"
