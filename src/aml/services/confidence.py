"""Rule confidence lifecycle management.

Handles auto-decay, deactivation, and confirmation of rules.
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from aml.config import settings
from aml.models.rule import Rule

logger = logging.getLogger(__name__)


async def apply_monthly_decay(db: AsyncSession) -> int:
    """Reduce confidence of rules not confirmed in the last 30 days.

    Rules that haven't been confirmed lose confidence_decay_monthly per period.
    Rules below confidence_deactivate_threshold are auto-deactivated.

    Returns number of rules affected.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    decay = settings.confidence_decay_monthly
    threshold = settings.confidence_deactivate_threshold

    # Find active rules not recently confirmed
    result = await db.execute(
        select(Rule)
        .where(Rule.active.is_(True))
        .where(
            (Rule.last_confirmed_at.is_(None)) | (Rule.last_confirmed_at < cutoff)
        )
    )
    rules = list(result.scalars().all())

    affected = 0
    for rule in rules:
        rule.confidence = max(0.0, rule.confidence - decay)

        if rule.confidence < threshold:
            rule.active = False
            logger.info("Auto-deactivated rule %s (confidence %.2f < %.2f)", rule.id, rule.confidence, threshold)

        affected += 1

    if affected:
        await db.commit()

    logger.info("Confidence decay: %d rules affected, decay=%.2f", affected, decay)
    return affected


async def confirm_rule(db: AsyncSession, rule_id, boost: float = 0.05) -> None:
    """Boost confidence when data confirms a rule."""
    rule = await db.get(Rule, rule_id)
    if not rule:
        return

    rule.confidence = min(1.0, rule.confidence + boost)
    rule.evidence_count += 1
    rule.last_confirmed_at = datetime.now(timezone.utc)
    await db.commit()


async def get_confidence_stats(db: AsyncSession, module_id: str | None = None) -> dict:
    """Get confidence distribution stats."""
    from sqlalchemy import func

    q = select(
        func.count(Rule.id).label("total"),
        func.avg(Rule.confidence).label("avg_confidence"),
        func.count(Rule.id).filter(Rule.confidence >= 0.8).label("auto_apply"),
        func.count(Rule.id).filter(Rule.confidence.between(0.6, 0.8)).label("strong"),
        func.count(Rule.id).filter(Rule.confidence.between(0.3, 0.6)).label("weak"),
        func.count(Rule.id).filter(Rule.confidence < 0.3).label("hypothesis"),
    ).where(Rule.active.is_(True))

    if module_id:
        q = q.where(Rule.module_id == module_id)

    result = await db.execute(q)
    row = result.one()

    return {
        "total_active": row.total,
        "avg_confidence": round(float(row.avg_confidence or 0), 3),
        "auto_apply": row.auto_apply,
        "strong": row.strong,
        "weak": row.weak,
        "hypothesis": row.hypothesis,
    }
