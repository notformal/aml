import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from aml.db import get_db
from aml.repositories.episode import get_episode
from aml.repositories.feedback import create_feedback, list_feedback_for_episode
from aml.schemas.feedback import FeedbackCreate, FeedbackResponse

router = APIRouter()


@router.post(
    "/episodes/{episode_id}/feedback", response_model=FeedbackResponse, status_code=201
)
async def create(
    episode_id: uuid.UUID, data: FeedbackCreate, db: AsyncSession = Depends(get_db)
):
    episode = await get_episode(db, episode_id)
    if not episode:
        raise HTTPException(404, "Episode not found")
    return await create_feedback(db, episode_id, data)


@router.get("/episodes/{episode_id}/feedback", response_model=list[FeedbackResponse])
async def list_all(episode_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await list_feedback_for_episode(db, episode_id)
