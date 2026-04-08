from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aml.models.project import Project
from aml.schemas.project import ProjectCreate


async def create_project(db: AsyncSession, data: ProjectCreate) -> Project:
    project = Project(id=data.id, name=data.name, config=data.config)
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


async def get_project(db: AsyncSession, project_id: str) -> Project | None:
    return await db.get(Project, project_id)


async def list_projects(db: AsyncSession) -> list[Project]:
    result = await db.execute(select(Project).order_by(Project.created_at.desc()))
    return list(result.scalars().all())
