"""Minimal ASGI app for the dedicated scheduler worker service.

The worker exists only to host the DB-driven scheduler pollers (reminders +
post-delivery follow-ups; see app.scheduler.jobs) in their own process, keeping
the web dyno scheduler-free and horizontally scalable. It shares no routes with
the web API - it serves a single /health endpoint so the platform health-check
(the same one the web service uses) passes, and starts the scheduler in its
lifespan.

Run as its OWN service: `uvicorn app.worker_app:app`. Exactly one instance
should run at a time. Migrations are owned by the web service; the worker does
not run them.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.logging import configure_logging, get_logger
from app.scheduler.jobs import scheduler, start_scheduler

log = get_logger("worker")


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    start_scheduler()
    log.info("scheduler_worker_started")
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)


app = FastAPI(title="Peaceway Scheduler Worker", lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "peaceway-scheduler"}
