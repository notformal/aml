import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from aml.models.base import Base


class Rule(Base):
    __tablename__ = "rules"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    module_id: Mapped[str] = mapped_column(ForeignKey("modules.id"), nullable=False)
    scope: Mapped[str] = mapped_column(String(20), default="module", server_default="module")
    rule_text: Mapped[str] = mapped_column(Text, nullable=False)
    rule_structured: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    rule_embedding = mapped_column(String, nullable=True)  # Vector(1536) in production via migration
    confidence: Mapped[float] = mapped_column(Float, default=0.5, server_default="0.5")
    evidence_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    tags: Mapped[list[str] | None] = mapped_column(JSON, default=list, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    parent_rule_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("rules.id"), nullable=True
    )
    source_project: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    last_confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    module: Mapped["Module"] = relationship(back_populates="rules")  # noqa: F821
    parent: Mapped["Rule | None"] = relationship(remote_side="Rule.id")
