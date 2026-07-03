from fastapi import APIRouter

from app.api.v1 import admin, ask, catalog, customers, health, orders, otp, prescriptions, reminders, requests, track, zones

router = APIRouter(prefix="/api/v1")
router.include_router(health.router)
router.include_router(customers.router)
router.include_router(otp.router)
router.include_router(zones.router)
router.include_router(requests.router)
router.include_router(ask.router)
router.include_router(reminders.router)
router.include_router(catalog.router)
router.include_router(orders.router)
router.include_router(prescriptions.router)
router.include_router(track.router)
router.include_router(admin.router)
