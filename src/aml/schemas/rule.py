from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

RuleScope = Literal["module", "project", "global"]


class RuleCreate(BaseModel):
    module_id: str = Field(max_length=100)
    rule_text: str
    rule_structured: dict | None = None
    confidence: float = Field(default=0.5, ge=0, le=1)
    tags: list[str] = Field(default_factory=list)
    scope: RuleScope = "module"
    parent_rule_id: UUID | None = None


class RuleUpdate(BaseModel):
    rule_text: str | None = None
    rule_structured: dict | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    tags: list[str] | None = None
    scope: RuleScope | None = None
    active: bool | None = None


class RuleResponse(BaseModel):
    id: UUID
    module_id: str
    scope: str
    rule_text: str
    rule_structured: dict | None
    confidence: float
    evidence_count: int
    tags: list[str]
    active: bool
    parent_rule_id: UUID | None
    source_project: str | None
    created_at: datetime
    updated_at: datetime
    last_confirmed_at: datetime | None

    model_config = {"from_attributes": True}
