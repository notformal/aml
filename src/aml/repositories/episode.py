import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aml.models.episode import Episode
from aml.models.feedback import Feedback
from aml.schemas.episode import EpisodeCreate


async def create_episode(
    db: AsyncSession, data: EpisodeCreate, embedding: list[float] | None = None
) -> Episode:
    episode = Episode(
        module_id=data.module_id,
        action=data.action,
        input_data=data.input_data,
        output_data=data.output_data,
        metadata_=data.metadata,
        input_embedding=embedding,
    )
    db.add(episode)
    await db.commit()
    await db.refresh(episode)
    return episode


async def get_episode(db: AsyncSession, episode_id: uuid.UUID) -> Episode | None:
    return await db.get(Episode, episode_id)


async def list_episodes(
    db: AsyncSession,
    module_id: str,
    limit: int = 50,
    offset: int = 0,
) -> list[Episode]:
    q = (
        select(Episode)
        .where(Episode.module_id == module_id)
        .order_by(Episode.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(q)
    return list(result.scalars().all())


async def search_similar_episodes(
    db: AsyncSession,
    module_id: str,
    embedding: list[float],
    top_k: int = 10,
    min_score: float = 0.0,
) -> list[dict]:
    """Find similar episodes by vector cosine distance, with avg feedback score."""
    avg_score = (
        select(func.avg(Feedback.score))
        .where(Feedback.episode_id == Episode.id)
        .correlate(Episode)
        .scalar_subquery()
    )

    q = (
        select(
            Episode,
            (1 - Episode.input_embedding.cosine_distance(embedding)).label("similarity"),
            avg_score.label("avg_score"),
        )
        .where(Episode.module_id == module_id)
        .where(Episode.input_embedding.isnot(None))
        .order_by(Episode.input_embedding.cosine_distance(embedding))
        .limit(top_k)
    )

    result = await db.execute(q)
    rows = []
    for episode, similarity, score in result.all():
        if min_score and score is not None and score < min_score:
            continue
        episode.avg_score = score
        rows.append(episode)
    return rows
