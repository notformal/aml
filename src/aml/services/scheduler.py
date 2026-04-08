"""Scheduler for periodic tasks: extraction, decay, retention.

Uses asyncio tasks — in production, replace with APScheduler or Celery Beat.
"""

import asyncio
import logging

from aml.db import async_session
from aml.models.module import Module
from aml.services.confidence import apply_monthly_decay
from aml.services.extraction import extract_patterns
from aml.services.retention import archive_old_episodes, cleanup_deactivated_rules

from sqlalchemy import select

logger = logging.getLogger(__name__)


async def run_daily_extraction():
    """Run extraction for all modules. Call once per day."""
    async with async_session() as db:
        result = await db.execute(select(Module))
        modules = result.scalars().all()

        for module in modules:
            try:
                await extract_patterns(db, module.id)
            except Exception:
                logger.exception("Extraction failed for %s", module.id)


async def run_monthly_decay():
    """Apply confidence decay. Call once per month."""
    async with async_session() as db:
        await apply_monthly_decay(db)


async def run_retention_cleanup():
    """Archive/delete old data. Call weekly."""
    async with async_session() as db:
        await archive_old_episodes(db, months=12)
        await cleanup_deactivated_rules(db, months=6)


async def scheduler_loop():
    """Simple scheduler loop. In production use APScheduler."""
    logger.info("Scheduler started")

    extraction_interval = 24 * 3600  # daily
    decay_interval = 30 * 24 * 3600  # monthly
    retention_interval = 7 * 24 * 3600  # weekly

    extraction_counter = 0
    decay_counter = 0
    retention_counter = 0
    tick = 3600  # check every hour

    while True:
        await asyncio.sleep(tick)
        extraction_counter += tick
        decay_counter += tick
        retention_counter += tick

        if extraction_counter >= extraction_interval:
            extraction_counter = 0
            try:
                await run_daily_extraction()
            except Exception:
                logger.exception("Daily extraction failed")

        if decay_counter >= decay_interval:
            decay_counter = 0
            try:
                await run_monthly_decay()
            except Exception:
                logger.exception("Monthly decay failed")

        if retention_counter >= retention_interval:
            retention_counter = 0
            try:
                await run_retention_cleanup()
            except Exception:
                logger.exception("Retention cleanup failed")
