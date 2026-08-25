import uuid
from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.crypto import EncryptedString
from app.db.session import Base


class InsurancePolicy(Base):
    __tablename__ = "insurance_policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    payer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    plan_name: Mapped[str] = mapped_column(String(255), nullable=True)
    member_id: Mapped[str] = mapped_column(EncryptedString(500), nullable=True)
    group_number: Mapped[str] = mapped_column(EncryptedString(500), nullable=True)
    effective_date: Mapped[date] = mapped_column(Date, nullable=True)

    # FHIR R4 Coverage resource, populated by the document intelligence pipeline
    fhir_coverage: Mapped[dict] = mapped_column(JSON, default=dict)

    source_document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="insurance_policies")
