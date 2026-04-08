import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from aml.models.base import Base


class Episode(Base):
    __tablename__ = "episodes"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    module_id: Mapped[str] = mapped_column(ForeignKey("modules.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(200), nullable=False)
    input_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    output_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    input_embedding = mapped_column(String, nullable=True)  # Vector(1536) in production via migration
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    module: Mapped["Module"] = relationship(back_populates="episodes")  # noqa: F821
    feedbacks: Mapped[list["Feedback"]] = relationship(back_populates="episode")  # noqa: F821
