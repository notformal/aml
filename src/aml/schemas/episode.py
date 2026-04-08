from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class EpisodeCreate(BaseModel):
    module_id: str = Field(max_length=100)
    action: str = Field(max_length=200)
    input_data: dict
    output_data: dict
    metadata: dict = Field(default_factory=dict)


class EpisodeResponse(BaseModel):
    id: UUID
    module_id: str
    action: str
    input_data: dict
    output_data: dict
    metadata: dict = Field(alias="metadata_")
    created_at: datetime
    avg_score: float | None = None

    model_config = {"from_attributes": True, "populate_by_name": True}
