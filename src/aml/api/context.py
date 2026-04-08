from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from aml.db import get_db
from aml.schemas.context import ContextRequest, ContextResponse
from aml.schemas.episode import EpisodeResponse
from aml.schemas.rule import RuleResponse
from aml.services.context import get_context

router = APIRouter()


@router.post("", response_model=ContextResponse)
async def get_ctx(data: ContextRequest, db: AsyncSession = Depends(get_db)):
    result = await get_context(
        db,
        module_id=data.module_id,
        query=data.query,
        top_k=data.top_k,
        min_score=data.min_score,
        min_confidence=data.min_confidence,
        tags=data.tags,
    )
    return ContextResponse(
        episodes=[EpisodeResponse.model_validate(e) for e in result["episodes"]],
        rules=[RuleResponse.model_validate(r) for r in result["rules"]],
    )
