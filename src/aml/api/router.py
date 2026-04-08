from fastapi import APIRouter

from aml.api.context import router as context_router
from aml.api.episodes import router as episodes_router
from aml.api.extract import router as extract_router
from aml.api.feedback import router as feedback_router
from aml.api.health import router as health_router
from aml.api.modules import router as modules_router
from aml.api.projects import router as projects_router
from aml.api.rules import router as rules_router
from aml.api.stats import router as stats_router

api_router = APIRouter()

api_router.include_router(health_router, tags=["health"])
api_router.include_router(projects_router, prefix="/projects", tags=["projects"])
api_router.include_router(modules_router, prefix="/modules", tags=["modules"])
api_router.include_router(episodes_router, prefix="/episodes", tags=["episodes"])
api_router.include_router(feedback_router, tags=["feedback"])
api_router.include_router(rules_router, prefix="/rules", tags=["rules"])
api_router.include_router(context_router, prefix="/context", tags=["context"])
api_router.include_router(stats_router, tags=["stats"])
api_router.include_router(extract_router, tags=["extraction"])
