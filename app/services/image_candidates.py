"""Staff review of scraped manufacturer images.

This module is the ONLY place in the scraping pipeline permitted to set
products.image_id. Track 2 stages candidates and stops; a human decides whether the
photograph actually shows the pack that gets dispensed.

Approval is deliberately two-step. A single tap is too easy to give by reflex, and
the failure mode here is a customer receiving a different pack from the one pictured
on a NAFDAC-regulated pharmacy. The second step asks one specific question — does the
pack size match — because pack size is the one field the matcher never checked.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, ImageCandidate, Product
from app.models.image_candidate import STATUS_APPROVED, STATUS_PENDING, STATUS_REJECTED
from app.services import file_storage


class CandidateNotReviewable(ValueError):
    """The candidate cannot be acted on (already judged, or matched to nothing)."""


async def pending_count(session: AsyncSession) -> int:
    return (
        await session.execute(
            select(func.count())
            .select_from(ImageCandidate)
            .where(
                ImageCandidate.status == STATUS_PENDING,
                ImageCandidate.product_id.is_not(None),
            )
        )
    ).scalar_one()


async def next_pending(
    session: AsyncSession, *, skip_ids: set[UUID] | None = None
) -> ImageCandidate | None:
    """Next candidate awaiting review.

    Unmatched rows (product_id NULL) are excluded: they exist to make the coverage
    gap visible, not to be approved onto a product they were never paired with.
    """
    stmt = select(ImageCandidate).where(
        ImageCandidate.status == STATUS_PENDING,
        ImageCandidate.product_id.is_not(None),
    )
    if skip_ids:
        stmt = stmt.where(ImageCandidate.id.notin_(list(skip_ids)))
    return (
        await session.execute(stmt.order_by(ImageCandidate.scraped_at).limit(1))
    ).scalar_one_or_none()


async def get_candidate(session: AsyncSession, candidate_id: UUID) -> ImageCandidate | None:
    return (
        await session.execute(select(ImageCandidate).where(ImageCandidate.id == candidate_id))
    ).scalar_one_or_none()


def _require_reviewable(candidate: ImageCandidate) -> None:
    if candidate.status != STATUS_PENDING:
        raise CandidateNotReviewable(f"Already {candidate.status}.")
    if candidate.product_id is None:
        raise CandidateNotReviewable("This candidate matched no product.")


async def approve(
    session: AsyncSession,
    candidate: ImageCandidate,
    image_bytes: bytes,
    admin_id: int,
) -> Product:
    """Publish the image onto its product. Callers must have confirmed pack size.

    Provenance travels with the bytes: source_url and match_basis are written onto
    the media asset so the origin of any published medicine photo stays answerable.
    """
    _require_reviewable(candidate)

    product = (
        await session.execute(select(Product).where(Product.id == candidate.product_id))
    ).scalar_one_or_none()
    if product is None:
        raise CandidateNotReviewable("The product this candidate pointed at is gone.")

    asset = await file_storage.store_image(
        session,
        image_bytes,
        uploaded_by=admin_id,
        source_url=candidate.image_url,
        match_basis=candidate.match_basis,
    )

    product.image_id = asset.id
    candidate.status = STATUS_APPROVED
    candidate.reviewed_by_telegram_id = admin_id
    candidate.image_sha256 = asset.sha256

    session.add(
        AuditLog(
            actor_telegram_id=admin_id,
            action="product_image_approved",
            entity="product",
            entity_id=str(product.id),
            detail={
                "candidate_id": str(candidate.id),
                "manufacturer": candidate.manufacturer,
                "source_url": candidate.image_url,
                "match_basis": candidate.match_basis,
                "pack_size_confirmed": True,
                # Recorded explicitly: a brand+form candidate reaches approval only
                # after a reviewer has also confirmed the strength off the pack.
                "strength_confirmed_by_reviewer": (candidate.match_basis or "").startswith(
                    "brandform="
                ),
            },
        )
    )
    return product


async def reject(
    session: AsyncSession, candidate: ImageCandidate, admin_id: int, reason: str | None = None
) -> None:
    _require_reviewable(candidate)
    candidate.status = STATUS_REJECTED
    candidate.reviewed_by_telegram_id = admin_id
    session.add(
        AuditLog(
            actor_telegram_id=admin_id,
            action="product_image_rejected",
            entity="image_candidate",
            entity_id=str(candidate.id),
            reason=reason,
            detail={
                "manufacturer": candidate.manufacturer,
                "source_url": candidate.image_url,
                "product_id": str(candidate.product_id) if candidate.product_id else None,
            },
        )
    )
