import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from aml.models.rule import Rule
from aml.schemas.rule import RuleCreate, RuleUpdate


async def create_rule(
    db: AsyncSession, data: RuleCreate, embedding: list[float] | None = None
) -> Rule:
    rule = Rule(
        module_id=data.module_id,
        rule_text=data.rule_text,
        rule_structured=data.rule_structured,
        confidence=data.confidence,
        tags=data.tags,
        scope=data.scope,
        parent_rule_id=data.parent_rule_id,
        rule_embedding=embedding,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


async def get_rule(db: AsyncSession, rule_id: uuid.UUID) -> Rule | None:
    return await db.get(Rule, rule_id)


async def update_rule(db: AsyncSession, rule_id: uuid.UUID, data: RuleUpdate) -> Rule | None:
    values = {k: v for k, v in data.model_dump(exclude_unset=True).items()}
    if not values:
        return await get_rule(db, rule_id)
    await db.execute(update(Rule).where(Rule.id == rule_id).values(**values))
    await db.commit()
    rule = await get_rule(db, rule_id)
    if rule:
        await db.refresh(rule)
    return rule


async def list_rules(
    db: AsyncSession,
    module_id: str | None = None,
    tags: list[str] | None = None,
    min_confidence: float = 0.0,
    active_only: bool = True,
    scope: str | None = None,
    limit: int = 100,
) -> list[Rule]:
    q = select(Rule).order_by(Rule.confidence.desc()).limit(limit)

    if active_only:
        q = q.where(Rule.active.is_(True))
    if module_id:
        q = q.where(Rule.module_id == module_id)
    if min_confidence > 0:
        q = q.where(Rule.confidence >= min_confidence)
    if scope:
        q = q.where(Rule.scope == scope)
    result = await db.execute(q)
    rules = list(result.scalars().all())

    # Filter by tags in Python (JSON column, no PG array operators)
    if tags:
        rules = [r for r in rules if r.tags and any(t in r.tags for t in tags)]

    return rules
