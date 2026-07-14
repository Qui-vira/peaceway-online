"""Dedicated scheduler worker: runs the reminder + post-delivery follow-up pollers.

Usage: python -m app.run_scheduler

Run this as its OWN process/service (e.g. a Railway "worker" service) so the web
dyno stays scheduler-free and horizontally scalable. Exactly one scheduler
worker should run at a time - the pollers are DB-driven and claim rows with
SELECT ... FOR UPDATE SKIP LOCKED, so a brief overlap during a deploy is safe,
but steady-state should be a single instance.

Migrations are owned by the web service (`alembic upgrade head`); this worker
does not run them. If it starts before the web has migrated, the pollers simply
error and retry on the next tick until the schema is present.
"""
from __future__ import annotations

import asyncio

from app.core.logging import configure_logging, get_logger
from app.scheduler.jobs import scheduler, start_scheduler

log = get_logger("run_scheduler")


async def main() -> None:
    configure_logging()
    start_scheduler()
    log.info("scheduler_worker_started")
    try:
        await asyncio.Event().wait()  # run until the process is signalled to stop
    finally:
        scheduler.shutdown(wait=False)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
