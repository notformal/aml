import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from aml.db import get_db
from aml.repositories.module import get_module
from aml.repositories.rule import create_rule, get_rule, list_rules, update_rule
from aml.schemas.rule import RuleCreate, RuleResponse, RuleUpdate
from aml.services.embedding import embed_text

router = APIRouter()


@router.post("", response_model=RuleResponse, status_code=201)
async def create(data: RuleCreate, db: AsyncSession = Depends(get_db)):
    module = await get_module(db, data.module_id)
    if not module:
        raise HTTPException(404, f"Module '{data.module_id}' not found")

    embedding = await embed_text(data.rule_text)
    return await create_rule(db, data, embedding=embedding)


@router.get("", response_model=list[RuleResponse])
async def list_all(
    module_id: str | None = None,
    tags: str | None = None,
    min_confidence: float = 0.0,
    active_only: bool = True,
    scope: str | None = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    tag_list = tags.split(",") if tags else None
    return await list_rules(
        db,
        module_id=module_id,
        tags=tag_list,
        min_confidence=min_confidence,
        active_only=active_only,
        scope=scope,
        limit=limit,
    )


@router.get("/{rule_id}", response_model=RuleResponse)
async def get(rule_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    rule = await get_rule(db, rule_id)
    if not rule:
        raise HTTPException(404, "Rule not found")
    return rule


@router.patch("/{rule_id}", response_model=RuleResponse)
async def update(
    rule_id: uuid.UUID, data: RuleUpdate, db: AsyncSession = Depends(get_db)
):
    existing = await get_rule(db, rule_id)
    if not existing:
        raise HTTPException(404, "Rule not found")
    return await update_rule(db, rule_id, data)
