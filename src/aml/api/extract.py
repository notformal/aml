"""Manual extraction trigger endpoint (for debug/admin)."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from aml.db import get_db
from aml.services.extraction import extract_patterns

router = APIRouter()


@router.post("/extract")
async def trigger_extraction(module_id: str, db: AsyncSession = Depends(get_db)):
    """Manually trigger pattern extraction for a module."""
    result = await extract_patterns(db, module_id)
    return result
