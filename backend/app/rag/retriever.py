"""Privacy-first healthcare context retrieval.

Rather than handing an LLM a user's entire medical history, each agent
declares the narrow scope of context it needs (e.g. the insurance agent
needs coverage + policy data, not medication history) and the retriever
returns only that slice, plus the top-k semantically relevant document
chunks for the current request. This bounds what leaves the database on
every LLM call.
"""

import uuid
from dataclasses import dataclass, field
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.claim import Claim
from app.models.document_chunk import DocumentChunk
from app.models.insurance import InsurancePolicy
from app.models.medication import Medication
from app.models.visit import Visit
from app.rag.embeddings import get_embedding_provider

Scope = Literal["insurance", "provider", "cost", "authorization", "safety"]

# Which structured record types each agent is allowed to read.
SCOPE_PERMISSIONS: dict[Scope, list[str]] = {
    "insurance": ["insurance_policies"],
    "provider": ["insurance_policies"],
    "cost": ["insurance_policies", "claims"],
    "authorization": ["insurance_policies", "visits"],
    "safety": ["medications", "visits"],
}


@dataclass
class HealthContext:
    scope: Scope
    insurance_policies: list[dict] = field(default_factory=list)
    claims: list[dict] = field(default_factory=list)
    medications: list[dict] = field(default_factory=list)
    visits: list[dict] = field(default_factory=list)
    relevant_document_excerpts: list[str] = field(default_factory=list)

    def to_prompt_context(self) -> str:
        parts = []
        if self.insurance_policies:
            parts.append(f"Insurance policies: {self.insurance_policies}")
        if self.claims:
            parts.append(f"Claims: {self.claims}")
        if self.medications:
            parts.append(f"Active medications: {self.medications}")
        if self.visits:
            parts.append(f"Recent visits: {self.visits}")
        if self.relevant_document_excerpts:
            joined = "\n---\n".join(self.relevant_document_excerpts)
            parts.append(f"Relevant document excerpts:\n{joined}")
        return "\n\n".join(parts) if parts else "No relevant records on file."


class HealthContextRetriever:
    def __init__(self, db: Session):
        self.db = db
        self.embedder = get_embedding_provider()

    def retrieve(self, user_id: uuid.UUID, scope: Scope, query: str, top_k: int = 4) -> HealthContext:
        allowed = SCOPE_PERMISSIONS[scope]
        context = HealthContext(scope=scope)

        if "insurance_policies" in allowed:
            rows = self.db.scalars(
                select(InsurancePolicy).where(InsurancePolicy.user_id == user_id)
            ).all()
            context.insurance_policies = [
                {
                    "payer_name": r.payer_name,
                    "plan_name": r.plan_name,
                    "member_id": r.member_id,
                    "group_number": r.group_number,
                    "fhir_coverage": r.fhir_coverage,
                }
                for r in rows
            ]

        if "claims" in allowed:
            rows = self.db.scalars(
                select(Claim).where(Claim.user_id == user_id).order_by(Claim.service_date.desc()).limit(10)
            ).all()
            context.claims = [
                {
                    "provider_name": r.provider_name,
                    "service_date": str(r.service_date) if r.service_date else None,
                    "billed_amount": float(r.billed_amount) if r.billed_amount else None,
                    "patient_responsibility": float(r.patient_responsibility) if r.patient_responsibility else None,
                    "status": r.status,
                }
                for r in rows
            ]

        if "medications" in allowed:
            rows = self.db.scalars(
                select(Medication).where(Medication.user_id == user_id, Medication.active.is_(True))
            ).all()
            context.medications = [
                {"name": r.name, "dosage": r.dosage, "frequency": r.frequency} for r in rows
            ]

        if "visits" in allowed:
            rows = self.db.scalars(
                select(Visit).where(Visit.user_id == user_id).order_by(Visit.visit_date.desc()).limit(10)
            ).all()
            context.visits = [
                {"provider_name": r.provider_name, "visit_type": r.visit_type, "reason": r.reason}
                for r in rows
            ]

        context.relevant_document_excerpts = self._search_document_chunks(user_id, query, top_k)
        return context

    def _search_document_chunks(self, user_id: uuid.UUID, query: str, top_k: int) -> list[str]:
        if not query.strip():
            return []
        query_embedding = self.embedder.embed(query)
        rows = self.db.scalars(
            select(DocumentChunk)
            .where(DocumentChunk.user_id == user_id)
            .order_by(DocumentChunk.embedding.cosine_distance(query_embedding))
            .limit(top_k)
        ).all()
        return [r.content for r in rows]
