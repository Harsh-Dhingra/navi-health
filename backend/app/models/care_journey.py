import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.session import Base


class CareJourney(Base):
    """A user-facing workflow, e.g. 'MRI - Left Knee', spanning multiple agent steps."""

    __tablename__ = "care_journeys"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    original_request: Mapped[str] = mapped_column(String(2000), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="in_progress")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="care_journeys")
    steps = relationship(
        "CareJourneyStep", back_populates="journey", cascade="all, delete-orphan", order_by="CareJourneyStep.sequence"
    )


class CareJourneyStep(Base):
    """One agent's contribution to a care journey (insurance check, prior auth, provider search, ...)."""

    __tablename__ = "care_journey_steps"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    journey_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("care_journeys.id"), nullable=False)

    sequence: Mapped[int] = mapped_column(Integer, default=0)
    step_type: Mapped[str] = mapped_column(String(50), nullable=False)
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending")

    data: Mapped[dict] = mapped_column(JSON, default=dict)
    requires_human_review: Mapped[bool] = mapped_column(default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    journey = relationship("CareJourney", back_populates="steps")
