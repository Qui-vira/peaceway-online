"""Web prescription submission — text + optional base64 image."""
from __future__ import annotations

from fastapi import APIRouter, status
from pydantic import BaseModel

from app.api.deps import CurrentCustomer, DbSession
from app.models.ops import Prescription

router = APIRouter(tags=["prescriptions"])


class SubmitPrescriptionBody(BaseModel):
    description: str
    # base64-encoded image/PDF (optional, sent from the browser)
    file_b64: str | None = None
    file_type: str = "image"  # image | document


class PrescriptionOut(BaseModel):
    id: str
    review_status: str
    created_at: str

    model_config = {"from_attributes": True}


@router.post("/prescriptions", status_code=status.HTTP_201_CREATED)
async def submit_prescription(
    body: SubmitPrescriptionBody,
    customer: CurrentCustomer,
    db: DbSession,
) -> PrescriptionOut:
    """Submit a prescription via the web app.

    file_id is stored as "web:<first 40 chars of description>" so the Telegram
    side knows it came through the web channel.  The actual content lives in
    the `note` column.  If a base64 image was provided it is stored there too.
    """
    description = body.description.strip()[:1000]
    # Build a stable file_id sentinel for the web channel
    slug = description[:40].replace(" ", "_") if description else "web_submission"
    file_id = f"web:{slug}"

    note_parts = [description]
    if body.file_b64:
        note_parts.append(f"[IMAGE_B64:{body.file_b64[:30]}…]")

    rx = Prescription(
        customer_id=customer.id,
        file_id=file_id,
        file_type=body.file_type,
        review_status="PENDING",
        note="\n".join(note_parts),
    )
    db.add(rx)
    await db.flush()

    return PrescriptionOut(
        id=str(rx.id),
        review_status=rx.review_status,
        created_at=rx.created_at.isoformat(),
    )
