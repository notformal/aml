import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aml.models.feedback import Feedback
from aml.schemas.feedback import FeedbackCreate


async def create_feedback(
    db: AsyncSession, episode_id: uuid.UUID, data: FeedbackCreate
) -> Feedback:
    fb = Feedback(
        episode_id=episode_id,
        score=data.score,
        feedback_type=data.feedback_type,
        source=data.source,
        details=data.details,
    )
    db.add(fb)
    await db.commit()
    await db.refresh(fb)
    return fb


async def list_feedback_for_episode(
    db: AsyncSession, episode_id: uuid.UUID
) -> list[Feedback]:
    result = await db.execute(
        select(Feedback)
        .where(Feedback.episode_id == episode_id)
        .order_by(Feedback.created_at.desc())
    )
    return list(result.scalars().all())
