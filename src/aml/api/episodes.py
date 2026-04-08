import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from aml.db import get_db
from aml.repositories.episode import create_episode, get_episode, list_episodes
from aml.repositories.module import get_module
from aml.schemas.episode import EpisodeCreate, EpisodeResponse
from aml.services.embedding import embed_text

router = APIRouter()


@router.post("", response_model=EpisodeResponse, status_code=201)
async def create(data: EpisodeCreate, db: AsyncSession = Depends(get_db)):
    module = await get_module(db, data.module_id)
    if not module:
        raise HTTPException(404, f"Module '{data.module_id}' not found")

    # Build text for embedding from input_data
    embed_source = json.dumps(data.input_data, ensure_ascii=False)[:8000]
    embedding = await embed_text(embed_source)

    episode = await create_episode(db, data, embedding=embedding)
    return episode


@router.get("/{episode_id}", response_model=EpisodeResponse)
async def get(episode_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    episode = await get_episode(db, episode_id)
    if not episode:
        raise HTTPException(404, "Episode not found")
    return episode


@router.get("", response_model=list[EpisodeResponse])
async def list_all(
    module_id: str,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    return await list_episodes(db, module_id=module_id, limit=limit, offset=offset)
