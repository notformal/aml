from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI

from aml.api.router import api_router
from aml.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    yield
    await app.state.redis.close()


app = FastAPI(
    title="AML — Adaptive Memory Layer",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(api_router, prefix="/api/v1")
