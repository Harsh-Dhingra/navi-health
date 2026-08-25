"""security hardening: field encryption columns, account lockout, refresh tokens

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-24

"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PHI columns now hold Fernet ciphertext (base64), which is longer than
    # the plaintext they replace — widen them. Text-typed columns (notes,
    # document_chunks.content, documents.extracted_data) already accept
    # arbitrary-length strings, so they need no DDL change for encryption.
    op.alter_column("insurance_policies", "member_id", type_=sa.String(500))
    op.alter_column("insurance_policies", "group_number", type_=sa.String(500))
    op.alter_column("claims", "claim_number", type_=sa.String(500))
    op.alter_column("visits", "reason", type_=sa.String(1500))
    op.alter_column(
        "documents", "extracted_data", type_=sa.Text(), postgresql_using="extracted_data::text"
    )

    op.add_column("users", sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False))
    op.add_column("users", sa.Column("failed_login_attempts", sa.Integer(), server_default="0", nullable=False))
    op.add_column("users", sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token_hash", sa.String(128), nullable=False, unique=True),
        sa.Column("revoked", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"])


def downgrade() -> None:
    op.drop_index("ix_refresh_tokens_token_hash", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
    op.drop_column("users", "locked_until")
    op.drop_column("users", "failed_login_attempts")
    op.drop_column("users", "is_active")
    op.alter_column(
        "documents", "extracted_data", type_=sa.JSON(), postgresql_using="extracted_data::json"
    )
    op.alter_column("visits", "reason", type_=sa.String(500))
    op.alter_column("claims", "claim_number", type_=sa.String(100))
    op.alter_column("insurance_policies", "group_number", type_=sa.String(100))
    op.alter_column("insurance_policies", "member_id", type_=sa.String(100))
