"""Module stats and observability endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aml.db import get_db
from aml.models.episode import Episode
from aml.models.extraction import ExtractionRun
from aml.models.feedback import Feedback
from aml.services.confidence import get_confidence_stats

router = APIRouter()


@router.get("/modules/{module_id}/stats")
async def module_stats(module_id: str, db: AsyncSession = Depends(get_db)):
    # Episode counts
    ep_count = await db.execute(
        select(func.count(Episode.id)).where(Episode.module_id == module_id)
    )
    total_episodes = ep_count.scalar() or 0

    # Feedback coverage
    episodes_with_fb = await db.execute(
        select(func.count(func.distinct(Feedback.episode_id))).where(
            Feedback.episode_id.in_(
                select(Episode.id).where(Episode.module_id == module_id)
            )
        )
    )
    feedback_count = episodes_with_fb.scalar() or 0
    coverage = round(feedback_count / total_episodes, 3) if total_episodes else 0

    # Average feedback score
    avg_score_result = await db.execute(
        select(func.avg(Feedback.score)).where(
            Feedback.episode_id.in_(
                select(Episode.id).where(Episode.module_id == module_id)
            )
        )
    )
    avg_score = avg_score_result.scalar()

    # Confidence stats
    confidence = await get_confidence_stats(db, module_id)

    # Last extraction
    last_run = await db.execute(
        select(ExtractionRun)
        .where(ExtractionRun.module_id == module_id)
        .order_by(ExtractionRun.created_at.desc())
        .limit(1)
    )
    run = last_run.scalars().first()

    return {
        "module_id": module_id,
        "total_episodes": total_episodes,
        "feedback_coverage": coverage,
        "avg_feedback_score": round(float(avg_score), 3) if avg_score else None,
        "rules": confidence,
        "last_extraction": {
            "at": run.created_at.isoformat() if run else None,
            "episodes_analyzed": run.episodes_analyzed if run else 0,
            "rules_created": run.rules_created if run else 0,
            "tokens_used": run.llm_tokens_used if run else 0,
        } if run else None,
    }
