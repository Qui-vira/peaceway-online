"""AI photo inventory intake pipeline (staff "Scan Stock From Photos").

Explicit stages, observable in logs:

  A. Image understanding      — the vision provider analyses the WHOLE batch
                                 (app.services.inventory_vision)
  B. Cross-image dedup        — provider-level (one batched request) plus the
                                 code-level safety net merge_duplicate_candidates
  C. Normalization            — pydantic-validated DetectedProduct candidates
  D. Database matching        — match_candidate against products + aliases
  E. Action planning          — plan_action per scan mode + confidence level

Nothing touches the real catalog until commit_scan_session, which routes every
write through services.products_admin so PriceHistory + admin activity logs are
recorded exactly like manual edits, and adds an AuditLog row for the scan.
"""
from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from decimal import Decimal
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models import AuditLog, Product, ProductPricing
from app.models.inventory_scan import (
    ACTION_ADD_STOCK,
    ACTION_CREATE,
    ACTION_DRAFT,
    ACTION_REVIEW,
    ACTION_SET_STOCK,
    MATCH_EXACT,
    MATCH_NEW,
    MATCH_PROBABLE,
    REVIEW_CONFIRMED,
    REVIEW_EDITED,
    REVIEW_PENDING,
    REVIEW_SKIPPED,
    SCAN_MODE_ADD,
    SCAN_MODE_DRAFT,
    SCAN_MODE_SET,
    SCAN_STATUS_ANALYSING,
    SCAN_STATUS_CANCELLED,
    SCAN_STATUS_COLLECTING,
    SCAN_STATUS_COMMITTED,
    SCAN_STATUS_FAILED,
    SCAN_STATUS_REVIEW,
    InventoryScanImage,
    InventoryScanItem,
    InventoryScanSession,
)
from app.services import catalog as catalog_service
from app.services.inventory_vision.schemas import DetectedProduct, InventoryScanResult
from app.services.products_admin import apply_change, apply_csv_row, create_product_from_name

log = get_logger("inventory-scan")

CONFIDENCE_HIGH = 0.85
CONFIDENCE_MEDIUM = 0.6

ACTIVE_STATUSES = (SCAN_STATUS_COLLECTING, SCAN_STATUS_ANALYSING, SCAN_STATUS_REVIEW)

# Exact CSV contract shared with the existing bulk importer.
CSV_HEADER = [
    "product_name", "category", "cost_price", "selling_price", "stock",
    "dosage", "prescription", "availability", "description",
]

EDITABLE_FIELDS = (
    "product_name", "category", "stock", "dosage", "prescription",
    "availability", "description", "cost_price", "selling_price",
)


def _norm(raw: str | None) -> str:
    return " ".join((raw or "").split()).lower()


# ── Session lifecycle ────────────────────────────────────────────────────────

async def get_active_session(
    db: AsyncSession, telegram_id: int
) -> InventoryScanSession | None:
    """The staff member's most recent still-open scan, if any."""
    stmt = (
        select(InventoryScanSession)
        .where(
            InventoryScanSession.admin_telegram_id == telegram_id,
            InventoryScanSession.status.in_(ACTIVE_STATUSES),
        )
        .order_by(InventoryScanSession.created_at.desc())
        .limit(1)
    )
    return (await db.execute(stmt)).scalars().first()


async def create_scan_session(
    db: AsyncSession, telegram_id: int, chat_id: int, scan_mode: str
) -> InventoryScanSession:
    scan = InventoryScanSession(
        admin_telegram_id=telegram_id, chat_id=chat_id, scan_mode=scan_mode
    )
    db.add(scan)
    await db.flush()
    log.info("scan_session_created", scan_id=str(scan.id), admin=telegram_id, mode=scan_mode)
    return scan


async def add_image(
    db: AsyncSession,
    scan: InventoryScanSession,
    telegram_file_id: str,
    file_unique_id: str,
    media_group_id: str | None = None,
) -> tuple[InventoryScanImage | None, int]:
    """Attach a photo; duplicates (same file_unique_id) are ignored.

    Returns (image_or_None_if_duplicate, total_image_count).
    """
    existing = (
        await db.execute(
            select(InventoryScanImage).where(InventoryScanImage.session_id == scan.id)
        )
    ).scalars().all()
    if any(img.file_unique_id == file_unique_id for img in existing):
        log.info("scan_image_duplicate", scan_id=str(scan.id), file_unique_id=file_unique_id)
        return None, len(existing)
    image = InventoryScanImage(
        session_id=scan.id,
        telegram_file_id=telegram_file_id,
        file_unique_id=file_unique_id,
        media_group_id=media_group_id,
        position=len(existing),
    )
    db.add(image)
    await db.flush()
    log.info("scan_image_added", scan_id=str(scan.id), position=image.position)
    return image, len(existing) + 1


async def cancel_scan(db: AsyncSession, scan: InventoryScanSession) -> None:
    scan.status = SCAN_STATUS_CANCELLED
    await db.flush()
    log.info("scan_session_cancelled", scan_id=str(scan.id))


async def fail_scan(db: AsyncSession, scan: InventoryScanSession, error: str) -> None:
    scan.status = SCAN_STATUS_FAILED
    scan.error = error[:2000]
    await db.flush()
    log.error("scan_session_failed", scan_id=str(scan.id), error=error)


# ── Stage B (safety net): merge duplicate detections ─────────────────────────

def merge_duplicate_candidates(
    products: Sequence[DetectedProduct],
) -> tuple[list[DetectedProduct], list[str]]:
    """Merge candidates with the same normalized name + dosage.

    The provider is asked to deduplicate across overlapping photos, but if it
    still returns the same product twice we keep the MAX count (never the sum —
    the detections may describe the same physical units seen in two photos).
    Different dosages are never merged: they may be different SKUs.
    """
    merged: dict[tuple[str, str], DetectedProduct] = {}
    order: list[tuple[str, str]] = []
    notes: list[str] = []
    for p in products:
        key = (_norm(p.product_name), _norm(p.dosage))
        if key not in merged:
            merged[key] = p
            order.append(key)
            continue
        ex = merged[key]
        merged[key] = ex.model_copy(
            update={
                "stock": max(ex.stock, p.stock),
                "source_images": sorted(set(ex.source_images) | set(p.source_images)),
                "identity_confidence": min(ex.identity_confidence, p.identity_confidence),
                "stock_count_confidence": min(
                    ex.stock_count_confidence, p.stock_count_confidence
                ),
                "counting_notes": (
                    f"{ex.counting_notes} | Duplicate detection merged; kept the larger "
                    "count instead of adding, to avoid double-counting overlapping photos."
                ).strip(" |"),
            }
        )
        notes.append(f"Merged duplicate detections of “{p.product_name}”.")
    return [merged[k] for k in order], notes


# ── Stage D: database matching ───────────────────────────────────────────────

def _dosage_compatible(a: str | None, b: str | None) -> bool:
    """True when the two dosage strings plausibly describe the same SKU."""
    if not a or not b:
        return True  # missing data is not evidence of a different SKU
    na, nb = _norm(a).replace(" ", ""), _norm(b).replace(" ", "")
    return na == nb or na in nb or nb in na


async def match_candidate(
    db: AsyncSession, product_name: str, dosage: str | None
) -> tuple[str, Product | None, float | None]:
    """Classify a detected product against the catalog.

    Returns (match_type, matched_product_or_None, match_confidence).
    """
    norm = _norm(product_name)
    results = await catalog_service.search_products(db, product_name, limit=8)
    if not results:
        # Fuzzy fallback on the leading token ("Relcer antacid gel" -> "Relcer").
        first = product_name.split()[0] if product_name.split() else ""
        if len(first) >= 4:
            results = await catalog_service.search_products(db, first, limit=8)

    for p in results:
        known = {_norm(p.name), _norm(p.generic_name)}
        if p.brand_name:
            known.add(_norm(p.brand_name))
        for alias in p.aliases:
            known.add(_norm(alias.alias_name))
        known.discard("")
        if norm in known:
            if not _dosage_compatible(dosage, p.strength):
                # Same name, different strength: possibly a different SKU —
                # never auto-merge (spec §6 stage D).
                return MATCH_PROBABLE, p, 0.6
            return MATCH_EXACT, p, 0.95

    if results:
        return MATCH_PROBABLE, results[0], 0.55
    return MATCH_NEW, None, None


# ── Stage E: action planning ─────────────────────────────────────────────────

def plan_action(
    match_type: str,
    identity_confidence: float,
    stock_count_confidence: float,
    scan_mode: str,
) -> str:
    if scan_mode == SCAN_MODE_DRAFT:
        return ACTION_DRAFT
    if min(identity_confidence, stock_count_confidence) < CONFIDENCE_MEDIUM:
        return ACTION_REVIEW  # low confidence never auto-commits
    if match_type == MATCH_EXACT:
        return ACTION_SET_STOCK if scan_mode == SCAN_MODE_SET else ACTION_ADD_STOCK
    if match_type == MATCH_NEW:
        return ACTION_CREATE
    return ACTION_REVIEW  # probable/uncertain matches need a human decision


def item_confidence_level(item: InventoryScanItem) -> str:
    """high | medium | low from the item's separate confidence axes."""
    values = [
        v
        for v in (item.identity_confidence, item.stock_count_confidence, item.match_confidence)
        if v is not None
    ]
    score = min(values) if values else 0.0
    if score >= CONFIDENCE_HIGH:
        return "high"
    if score >= CONFIDENCE_MEDIUM:
        return "medium"
    return "low"


# ── Pipeline: turn a validated provider result into reviewable items ────────

async def run_analysis(
    db: AsyncSession, scan: InventoryScanSession, result: InventoryScanResult
) -> InventoryScanSession:
    """Stages B–E over an already-validated provider result."""
    log.info("scan_analysis_started", scan_id=str(scan.id), detections=len(result.products))
    await db.refresh(scan, ["images", "items"])  # async-safe collection load

    candidates, merge_notes = merge_duplicate_candidates(result.products)
    if merge_notes:
        log.info("scan_duplicates_merged", scan_id=str(scan.id), merged=len(merge_notes))

    # Clear items from a previous (retried) analysis of this session.
    scan.items.clear()
    await db.flush()

    counts = {"existing": 0, "new": 0, "needs_review": 0}
    for idx, cand in enumerate(candidates):
        match_type, product, match_conf = await match_candidate(
            db, cand.product_name, cand.dosage
        )
        action = plan_action(
            match_type, cand.identity_confidence, cand.stock_count_confidence, scan.scan_mode
        )
        item = InventoryScanItem(
            session_id=scan.id,
            item_index=idx,
            product_name=cand.product_name,
            category=cand.category,
            dosage=cand.dosage,
            prescription=cand.prescription,
            availability=True,
            description=cand.description,
            detected_stock=cand.stock,
            counting_notes=cand.counting_notes or None,
            source_images=cand.source_images,
            identity_confidence=cand.identity_confidence,
            stock_count_confidence=cand.stock_count_confidence,
            match_confidence=match_conf,
            match_type=match_type,
            matched_product_id=product.id if product else None,
            proposed_action=action,
        )
        db.add(item)
        scan.items.append(item)
        if action == ACTION_REVIEW:
            counts["needs_review"] += 1
        elif match_type == MATCH_EXACT:
            counts["existing"] += 1
        else:
            counts["new"] += 1
        log.info(
            "scan_item_planned",
            scan_id=str(scan.id),
            item=cand.product_name,
            match=match_type,
            action=action,
            stock=cand.stock,
        )

    for img in scan.images:
        img.status = "unreadable" if img.position in result.unreadable_images else "analysed"

    scan.warnings = list(result.warnings) + merge_notes
    scan.analysis_summary = {
        "detected": len(candidates),
        **counts,
        "unreadable_images": result.unreadable_images,
    }
    scan.status = SCAN_STATUS_REVIEW
    await db.flush()
    log.info("scan_analysis_complete", scan_id=str(scan.id), **scan.analysis_summary)
    return scan


# ── Human review / corrections ───────────────────────────────────────────────

def _record_correction(item: InventoryScanItem, field: str, old, new, admin_id: int) -> None:
    entry = {
        "field": field,
        "old": None if old is None else str(old),
        "new": None if new is None else str(new),
        "admin_id": admin_id,
        "at": datetime.now(timezone.utc).isoformat(),
    }
    # Reassign so SQLAlchemy sees the JSON change.
    item.corrections = list(item.corrections or []) + [entry]


def _replan_after_edit(item: InventoryScanItem, scan_mode: str) -> None:
    """A human decision lifts needs_review: plan from the (possibly new) match."""
    if scan_mode == SCAN_MODE_DRAFT:
        item.proposed_action = ACTION_DRAFT
    elif item.matched_product_id is not None:
        item.proposed_action = (
            ACTION_SET_STOCK if scan_mode == SCAN_MODE_SET else ACTION_ADD_STOCK
        )
    else:
        item.proposed_action = ACTION_CREATE
    item.review_status = REVIEW_EDITED


async def apply_correction(
    db: AsyncSession,
    item: InventoryScanItem,
    field: str,
    new_value,
    admin_id: int,
    scan_mode: str,
) -> None:
    """Apply one human edit, recording original AI value, editor, and timestamp."""
    if field not in EDITABLE_FIELDS:
        raise ValueError(f"Field not editable: {field}")

    if field == "stock":
        val = int(str(new_value).strip())
        if val < 0:
            raise ValueError("Stock must be 0 or more.")
        _record_correction(item, "stock", item.detected_stock, val, admin_id)
        item.detected_stock = val
        item.stock_count_confidence = 1.0  # human-counted
    elif field == "product_name":
        val = " ".join(str(new_value).split())[:255]
        if not val:
            raise ValueError("Name must not be empty.")
        _record_correction(item, "product_name", item.product_name, val, admin_id)
        item.product_name = val
        item.identity_confidence = 1.0
    elif field == "category":
        from app.services.products_admin import VALID_CATEGORIES

        if new_value not in VALID_CATEGORIES:
            raise ValueError("Unknown category.")
        _record_correction(item, "category", item.category, new_value, admin_id)
        item.category = new_value
    elif field == "prescription":
        if new_value not in ("OTC", "Rx", "uncertain"):
            raise ValueError("Prescription must be OTC, Rx or uncertain.")
        _record_correction(item, "prescription", item.prescription, new_value, admin_id)
        item.prescription = new_value
    elif field == "availability":
        val = bool(new_value)
        _record_correction(item, "availability", item.availability, val, admin_id)
        item.availability = val
    elif field in ("cost_price", "selling_price"):
        val = Decimal(str(new_value).replace(",", "").replace("₦", "").strip())
        if val < 0:
            raise ValueError("Price must be 0 or more.")
        _record_correction(item, field, getattr(item, field), val, admin_id)
        setattr(item, field, val)
    else:  # dosage, description — free text
        val = str(new_value).strip() or None
        limit = 100 if field == "dosage" else 1000
        _record_correction(item, field, getattr(item, field), val, admin_id)
        setattr(item, field, val and val[:limit])

    _replan_after_edit(item, scan_mode)
    await db.flush()
    log.info("scan_item_edited", item_id=str(item.id), field=field, admin=admin_id)


async def set_item_match(
    db: AsyncSession,
    item: InventoryScanItem,
    product: Product | None,
    admin_id: int,
    scan_mode: str,
) -> None:
    """Human re-match: link to an existing product, or mark as brand new (None)."""
    old = str(item.matched_product_id) if item.matched_product_id else None
    new = str(product.id) if product else None
    _record_correction(item, "matched_product_id", old, new, admin_id)
    item.matched_product_id = product.id if product else None
    item.match_type = MATCH_EXACT if product else MATCH_NEW
    item.match_confidence = 1.0  # human decision
    _replan_after_edit(item, scan_mode)
    await db.flush()
    log.info("scan_item_rematched", item_id=str(item.id), product=new, admin=admin_id)


def confirm_safe_items(scan: InventoryScanSession) -> int:
    """Bulk-confirm HIGH-confidence items that don't need review. Returns count."""
    confirmed = 0
    for item in scan.items:
        if (
            item.review_status == REVIEW_PENDING
            and item.proposed_action != ACTION_REVIEW
            and item_confidence_level(item) == "high"
        ):
            item.review_status = REVIEW_CONFIRMED
            confirmed += 1
    return confirmed


# ── Commit ───────────────────────────────────────────────────────────────────

def commit_plan(scan: InventoryScanSession) -> dict:
    """What Confirm will do: counts for the pre-commit summary screen."""
    plan = {"update": 0, "create": 0, "skip": 0, "draft": 0}
    for item in scan.items:
        if item.review_status in (REVIEW_SKIPPED, REVIEW_PENDING):
            plan["skip"] += 1
        elif scan.scan_mode == SCAN_MODE_DRAFT:
            plan["draft"] += 1
        elif item.matched_product_id is not None:
            plan["update"] += 1
        else:
            plan["create"] += 1
    return plan


async def commit_scan_session(
    db: AsyncSession, scan: InventoryScanSession, admin_id: int
) -> dict:
    """Apply the reviewed scan to the real catalog in one transaction.

    Only confirmed/edited items are applied; pending and skipped items are left
    untouched. Every product write goes through products_admin.apply_change /
    apply_csv_row so PriceHistory + AdminActivityLog stay consistent. The caller
    owns the transaction: any exception must roll the whole session back.
    """
    if scan.status != SCAN_STATUS_REVIEW:
        raise ValueError(f"Session is not reviewable (status={scan.status}).")
    await db.refresh(scan, ["images", "items"])  # async-safe collection load

    mode = scan.scan_mode
    reason = f"AI photo scan {scan.id} ({mode})"
    summary = {"updated": 0, "created": 0, "skipped": 0, "drafted": 0, "items": []}
    log.info("scan_commit_started", scan_id=str(scan.id), mode=mode, admin=admin_id)

    for item in scan.items:
        record = {
            "name": item.product_name,
            "detected_stock": item.detected_stock,
            "review_status": item.review_status,
            "corrections": len(item.corrections or []),
        }
        if item.review_status not in (REVIEW_CONFIRMED, REVIEW_EDITED):
            summary["skipped"] += 1
            record["result"] = "skipped"
            summary["items"].append(record)
            continue

        if mode == SCAN_MODE_DRAFT:
            item.committed = True
            summary["drafted"] += 1
            record["result"] = "drafted"
            summary["items"].append(record)
            continue

        if item.matched_product_id is not None:
            product = await db.get(Product, item.matched_product_id)
            if product is None:
                raise ValueError(
                    f"Matched product no longer exists for “{item.product_name}”."
                )
            pricing = (
                await db.execute(
                    select(ProductPricing).where(ProductPricing.product_id == product.id)
                )
            ).scalar_one_or_none()
            current = pricing.stock_qty if pricing else 0
            new_stock = (
                item.detected_stock
                if mode == SCAN_MODE_SET
                else current + item.detected_stock
            )
            await apply_change(db, product, "stock", str(new_stock), admin_id, reason=reason)
            item.committed = True
            summary["updated"] += 1
            record.update(result="updated", product_id=str(product.id), new_stock=new_stock)
        else:
            product = await create_product_from_name(
                db, item.product_name, admin_id, strength=item.dosage, reason=reason
            )
            row = {
                "stock": str(item.detected_stock),
                "category": item.category or "",
                "availability": "yes" if item.availability else "no",
                "description": item.description or "",
                "dosage": item.dosage or "",
            }
            # "uncertain" prescription is deliberately omitted: the product then
            # keeps requires_review=True and waits for pharmacist clearance.
            if item.prescription in ("OTC", "Rx"):
                row["prescription"] = item.prescription
            if item.cost_price is not None:
                row["cost_price"] = str(item.cost_price)
            if item.selling_price is not None:
                row["selling_price"] = str(item.selling_price)
            await apply_csv_row(db, product, row, admin_id)
            item.committed = True
            summary["created"] += 1
            record.update(result="created", product_id=str(product.id))
        summary["items"].append(record)

    scan.status = SCAN_STATUS_COMMITTED
    scan.committed_at = datetime.now(timezone.utc)
    scan.commit_summary = summary
    db.add(
        AuditLog(
            actor_telegram_id=admin_id,
            action="inventory_scan_commit",
            entity="inventory_scan_session",
            entity_id=str(scan.id),
            detail={
                "scan_mode": mode,
                "images": len(scan.images),
                "warnings": scan.warnings or [],
                **summary,
            },
        )
    )
    await db.flush()
    log.info(
        "scan_commit_complete",
        scan_id=str(scan.id),
        updated=summary["updated"],
        created=summary["created"],
        skipped=summary["skipped"],
    )
    return summary


# ── CSV export ───────────────────────────────────────────────────────────────

def generate_csv(scan: InventoryScanSession) -> str:
    """Reviewed session data as CSV text with the exact importer header."""
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(CSV_HEADER)
    for item in scan.items:
        if item.review_status == REVIEW_SKIPPED:
            continue
        writer.writerow(
            [
                item.product_name,
                item.category or "",
                "" if item.cost_price is None else str(item.cost_price),
                "" if item.selling_price is None else str(item.selling_price),
                item.detected_stock,
                item.dosage or "",
                item.prescription if item.prescription in ("OTC", "Rx") else "",
                "yes" if item.availability else "no",
                item.description or "",
            ]
        )
    return buf.getvalue()
