from pydantic import BaseModel, Field

from aml.schemas.episode import EpisodeResponse
from aml.schemas.rule import RuleResponse


class ContextRequest(BaseModel):
    query: str
    module_id: str
    top_k: int = Field(default=10, ge=1, le=100)
    min_score: float = Field(default=0.0, ge=0, le=1)
    min_confidence: float = Field(default=0.3, ge=0, le=1)
    tags: list[str] | None = None


class ContextResponse(BaseModel):
    episodes: list[EpisodeResponse]
    rules: list[RuleResponse]
