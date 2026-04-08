"""Data retention: archive old episodes, cleanup deactivated rules."""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from aml.models.episode import Episode
from aml.models.feedback import Feedback
from aml.models.rule import Rule

logger = logging.getLogger(__name__)


async def archive_old_episodes(db: AsyncSession, months: int = 12) -> int:
    """Delete episodes older than N months (and their feedback).

    In production, move to cold storage instead of deleting.
    Returns count of deleted episodes.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=months * 30)

    # Find old episode IDs
    result = await db.execute(
        select(Episode.id).where(Episode.created_at < cutoff)
    )
    old_ids = [row[0] for row in result.all()]

    if not old_ids:
        return 0

    # Delete feedback first (FK constraint)
    await db.execute(
        delete(Feedback).where(Feedback.episode_id.in_(old_ids))
    )

    # Delete episodes
    await db.execute(
        delete(Episode).where(Episode.id.in_(old_ids))
    )

    await db.commit()
    logger.info("Archived %d episodes older than %d months", len(old_ids), months)
    return len(old_ids)


async def cleanup_deactivated_rules(db: AsyncSession, months: int = 6) -> int:
    """Delete rules that have been deactivated for more than N months."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=months * 30)

    result = await db.execute(
        delete(Rule)
        .where(Rule.active.is_(False))
        .where(Rule.updated_at < cutoff)
        .returning(Rule.id)
    )
    deleted = result.all()

    if deleted:
        await db.commit()

    logger.info("Cleaned up %d deactivated rules", len(deleted))
    return len(deleted)
