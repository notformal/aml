from datetime import datetime

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    id: str = Field(max_length=50)
    name: str = Field(max_length=200)
    config: dict = Field(default_factory=dict)


class ProjectResponse(BaseModel):
    id: str
    name: str
    config: dict
    created_at: datetime

    model_config = {"from_attributes": True}
