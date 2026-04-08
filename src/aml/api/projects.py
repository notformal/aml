from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from aml.db import get_db
from aml.repositories.project import create_project, get_project, list_projects
from aml.schemas.project import ProjectCreate, ProjectResponse

router = APIRouter()


@router.post("", response_model=ProjectResponse, status_code=201)
async def create(data: ProjectCreate, db: AsyncSession = Depends(get_db)):
    existing = await get_project(db, data.id)
    if existing:
        raise HTTPException(409, f"Project '{data.id}' already exists")
    return await create_project(db, data)


@router.get("", response_model=list[ProjectResponse])
async def list_all(db: AsyncSession = Depends(get_db)):
    return await list_projects(db)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get(project_id: str, db: AsyncSession = Depends(get_db)):
    project = await get_project(db, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    return project
