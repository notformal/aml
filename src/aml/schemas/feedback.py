from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

FeedbackType = Literal["auto_metric", "human", "ab_test", "downstream"]


class FeedbackCreate(BaseModel):
    score: float = Field(ge=0, le=1)
    feedback_type: FeedbackType
    source: str | None = Field(default=None, max_length=200)
    details: dict = Field(default_factory=dict)


class FeedbackResponse(BaseModel):
    id: UUID
    episode_id: UUID
    score: float
    feedback_type: str
    source: str | None
    details: dict
    created_at: datetime

    model_config = {"from_attributes": True}
