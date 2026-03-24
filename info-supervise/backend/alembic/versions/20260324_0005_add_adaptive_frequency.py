"""add adaptive frequency tracking column

Revision ID: 20260324_0005
Revises: 20260324_0004
Create Date: 2026-03-24
"""
from alembic import op
import sqlalchemy as sa

revision = "20260324_0005"
down_revision = "20260324_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "app_status_current",
        sa.Column("consecutive_no_change", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("app_status_current", "consecutive_no_change")
