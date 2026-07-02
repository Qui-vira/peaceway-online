from fastapi import APIRouter

from app.api.v1 import ask, customers, health, requests, zones

router = APIRouter(prefix="/api/v1")
router.include_router(health.router)
router.include_router(customers.router)
router.include_router(zones.router)
router.include_router(requests.router)
router.include_router(ask.router)
