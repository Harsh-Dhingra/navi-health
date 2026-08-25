"""audit_logs.user_id: allow account deletion via ON DELETE SET NULL

Found by an actual live smoke test: deleting a user 500'd with a
ForeignKeyViolation because audit_logs (e.g. the "account_created" row
written at registration) still referenced the user being deleted, and the
original FK had no ON DELETE behavior.

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-25

"""
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("audit_logs_user_id_fkey", "audit_logs", type_="foreignkey")
    op.create_foreign_key(
        "audit_logs_user_id_fkey", "audit_logs", "users", ["user_id"], ["id"], ondelete="SET NULL"
    )


def downgrade() -> None:
    op.drop_constraint("audit_logs_user_id_fkey", "audit_logs", type_="foreignkey")
    op.create_foreign_key("audit_logs_user_id_fkey", "audit_logs", "users", ["user_id"], ["id"])
