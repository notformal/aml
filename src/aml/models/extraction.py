import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from aml.models.base import Base


class ExtractionRun(Base):
    __tablename__ = "extraction_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    module_id: Mapped[str] = mapped_column(String(100), nullable=True)
    episodes_analyzed: Mapped[int] = mapped_column(Integer, default=0)
    rules_created: Mapped[int] = mapped_column(Integer, default=0)
    rules_updated: Mapped[int] = mapped_column(Integer, default=0)
    rules_deactivated: Mapped[int] = mapped_column(Integer, default=0)
    llm_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    llm_tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
