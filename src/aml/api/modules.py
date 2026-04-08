from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from aml.db import get_db
from aml.repositories.module import create_module, get_module, list_modules
from aml.repositories.project import get_project
from aml.schemas.module import ModuleCreate, ModuleResponse

router = APIRouter()


@router.post("", response_model=ModuleResponse, status_code=201)
async def create(data: ModuleCreate, db: AsyncSession = Depends(get_db)):
    project = await get_project(db, data.project_id)
    if not project:
        raise HTTPException(404, f"Project '{data.project_id}' not found")
    existing = await get_module(db, data.id)
    if existing:
        raise HTTPException(409, f"Module '{data.id}' already exists")
    return await create_module(db, data)


@router.get("", response_model=list[ModuleResponse])
async def list_all(
    project_id: str | None = None, db: AsyncSession = Depends(get_db)
):
    return await list_modules(db, project_id=project_id)


@router.get("/{module_id}", response_model=ModuleResponse)
async def get(module_id: str, db: AsyncSession = Depends(get_db)):
    module = await get_module(db, module_id)
    if not module:
        raise HTTPException(404, "Module not found")
    return module
