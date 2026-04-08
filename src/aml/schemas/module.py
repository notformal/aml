from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ModuleType = Literal["generation", "recommendation", "analysis", "classification", "optimization"]


class ModuleCreate(BaseModel):
    id: str = Field(max_length=100)
    project_id: str = Field(max_length=50)
    name: str = Field(max_length=200)
    module_type: ModuleType
    config: dict = Field(default_factory=dict)


class ModuleResponse(BaseModel):
    id: str
    project_id: str
    name: str
    module_type: str
    config: dict
    created_at: datetime

    model_config = {"from_attributes": True}
