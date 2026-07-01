from fastapi import APIRouter
from app.core.config import get_settings

router = APIRouter(tags=["web-health"])


@router.get("/health")
async def web_health() -> dict:
    """Health check for the web frontend connection.

    Distinct from the root /health used by Railway's internal health checks.
    The web frontend calls this to confirm the API is reachable before rendering
    dynamic content.
    """
    settings = get_settings()
    return {
        "status": "ok",
        "service": "peaceway-online",
        "version": "1.0.0",
        "environment": settings.env,
    }
