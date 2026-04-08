from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from aml.db import get_db

router = APIRouter()


@router.get("/health")
async def health(request: Request, db: AsyncSession = Depends(get_db)):
    checks = {"api": "ok", "database": "error", "redis": "error"}

    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        pass

    try:
        pong = await request.app.state.redis.ping()
        if pong:
            checks["redis"] = "ok"
    except Exception:
        pass

    healthy = all(v == "ok" for v in checks.values())
    return {"status": "healthy" if healthy else "degraded", "checks": checks}
