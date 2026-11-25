"""Lightweight in-process scheduler.

Runs `run_daily_jobs` every SCHEDULER_INTERVAL_MINUTES. When several API workers run
it at once on PostgreSQL, a session-level advisory lock ensures only one executes per tick;
the jobs are idempotent regardless, so this only avoids wasted work.
"""
import asyncio
import logging
from contextlib import suppress

from sqlalchemy import text

from app.core.config import settings
from app.core.database import SessionLocal, engine
from app.services.jobs import run_daily_jobs

logger = logging.getLogger(__name__)

ADVISORY_LOCK_KEY = 74_201_001  # arbitrary app-wide constant
STARTUP_DELAY_SECONDS = 20


def run_jobs_once() -> None:
    lock_conn = None
    try:
        if engine.dialect.name == "postgresql":
            lock_conn = engine.connect()
            acquired = lock_conn.execute(
                text("SELECT pg_try_advisory_lock(:k)"), {"k": ADVISORY_LOCK_KEY}
            ).scalar()
            if not acquired:
                logger.info("Scheduled jobs already running in another worker; skipping this tick")
                return
        db = SessionLocal()
        try:
            run_daily_jobs(db)
        finally:
            db.close()
    except Exception:
        logger.exception("Scheduled jobs failed")
    finally:
        if lock_conn is not None:
            with suppress(Exception):
                lock_conn.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": ADVISORY_LOCK_KEY})
            lock_conn.close()


async def scheduler_loop() -> None:
    interval = max(5, settings.SCHEDULER_INTERVAL_MINUTES) * 60
    await asyncio.sleep(STARTUP_DELAY_SECONDS)
    while True:
        await asyncio.to_thread(run_jobs_once)
        await asyncio.sleep(interval)
