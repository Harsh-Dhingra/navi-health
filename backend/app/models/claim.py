import uuid
from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.crypto import EncryptedString
from app.db.session import Base


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    policy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("insurance_policies.id"), nullable=True
    )

    claim_number: Mapped[str] = mapped_column(EncryptedString(500), nullable=True)
    provider_name: Mapped[str] = mapped_column(String(255), nullable=True)
    service_date: Mapped[date] = mapped_column(Date, nullable=True)
    billed_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=True)
    allowed_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=True)
    patient_responsibility: Mapped[float] = mapped_column(Numeric(10, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="submitted")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="claims")
    eob = relationship("ExplanationOfBenefits", back_populates="claim", uselist=False)


class ExplanationOfBenefits(Base):
    __tablename__ = "explanations_of_benefits"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    claim_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("claims.id"), nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True)

    summary: Mapped[str] = mapped_column(String(2000), nullable=True)
    # FHIR R4 ExplanationOfBenefit resource
    fhir_eob: Mapped[dict] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    claim = relationship("Claim", back_populates="eob")
