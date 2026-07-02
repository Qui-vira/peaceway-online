from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import DbSession
from app.models.ops import DeliveryZone

router = APIRouter(tags=["zones"])


@router.get("/zones")
async def list_zones(db: DbSession) -> list[dict]:
    """Return all active delivery zones with fee and ETA."""
    rows = (
        await db.execute(
            select(DeliveryZone)
            .where(DeliveryZone.is_active.is_(True))
            .order_by(DeliveryZone.name)
        )
    ).scalars().all()
    return [
        {
            "id": str(z.id),
            "name": z.name,
            "fee": float(z.fee),
            "eta_minutes": z.eta_minutes,
        }
        for z in rows
    ]
