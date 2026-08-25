"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-08-24

"""
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("storage_path", sa.String(1000), nullable=False),
        sa.Column("document_type", sa.String(50)),
        sa.Column("processed", sa.Boolean, default=False),
        sa.Column("extracted_data", sa.JSON, default=dict),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "document_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("chunk_index", sa.Integer, default=0),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("embedding", Vector(1024)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.execute(
        "CREATE INDEX document_chunks_embedding_idx ON document_chunks "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )

    op.create_table(
        "insurance_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("payer_name", sa.String(255), nullable=False),
        sa.Column("plan_name", sa.String(255)),
        sa.Column("member_id", sa.String(100)),
        sa.Column("group_number", sa.String(100)),
        sa.Column("effective_date", sa.Date),
        sa.Column("fhir_coverage", sa.JSON, default=dict),
        sa.Column("source_document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "claims",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("policy_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("insurance_policies.id")),
        sa.Column("claim_number", sa.String(100)),
        sa.Column("provider_name", sa.String(255)),
        sa.Column("service_date", sa.Date),
        sa.Column("billed_amount", sa.Numeric(10, 2)),
        sa.Column("allowed_amount", sa.Numeric(10, 2)),
        sa.Column("patient_responsibility", sa.Numeric(10, 2)),
        sa.Column("status", sa.String(50), default="submitted"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "explanations_of_benefits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("claim_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("claims.id"), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id")),
        sa.Column("summary", sa.String(2000)),
        sa.Column("fhir_eob", sa.JSON, default=dict),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "medications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("dosage", sa.String(100)),
        sa.Column("frequency", sa.String(100)),
        sa.Column("prescriber", sa.String(255)),
        sa.Column("start_date", sa.Date),
        sa.Column("end_date", sa.Date),
        sa.Column("active", sa.Boolean, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "visits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("provider_name", sa.String(255)),
        sa.Column("visit_type", sa.String(100)),
        sa.Column("visit_date", sa.Date),
        sa.Column("reason", sa.String(500)),
        sa.Column("notes", sa.Text),
        sa.Column("fhir_encounter", sa.JSON, default=dict),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "care_journeys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("original_request", sa.String(2000)),
        sa.Column("status", sa.String(50), default="in_progress"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "care_journey_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("journey_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("care_journeys.id"), nullable=False),
        sa.Column("sequence", sa.Integer, default=0),
        sa.Column("step_type", sa.String(50), nullable=False),
        sa.Column("agent_name", sa.String(100), nullable=False),
        sa.Column("status", sa.String(50), default="pending"),
        sa.Column("data", sa.JSON, default=dict),
        sa.Column("requires_human_review", sa.Boolean, default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("agent_name", sa.String(100)),
        sa.Column("description", sa.String(2000)),
        sa.Column("event_metadata", sa.JSON, default=dict),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("care_journey_steps")
    op.drop_table("care_journeys")
    op.drop_table("visits")
    op.drop_table("medications")
    op.drop_table("explanations_of_benefits")
    op.drop_table("claims")
    op.drop_table("insurance_policies")
    op.drop_table("document_chunks")
    op.drop_table("documents")
    op.drop_table("users")
