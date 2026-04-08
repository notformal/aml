from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aml.models.module import Module
from aml.schemas.module import ModuleCreate


async def create_module(db: AsyncSession, data: ModuleCreate) -> Module:
    module = Module(
        id=data.id,
        project_id=data.project_id,
        name=data.name,
        module_type=data.module_type,
        config=data.config,
    )
    db.add(module)
    await db.commit()
    await db.refresh(module)
    return module


async def get_module(db: AsyncSession, module_id: str) -> Module | None:
    return await db.get(Module, module_id)


async def list_modules(db: AsyncSession, project_id: str | None = None) -> list[Module]:
    q = select(Module).order_by(Module.created_at.desc())
    if project_id:
        q = q.where(Module.project_id == project_id)
    result = await db.execute(q)
    return list(result.scalars().all())
