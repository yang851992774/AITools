"""extend metadata columns and add tags

Revision ID: 20260324_0004
Revises: 20260324_0003
Create Date: 2026-03-24
"""
from alembic import op
import sqlalchemy as sa

revision = "20260324_0004"
down_revision = "20260324_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("watched_apps", sa.Column("tags", sa.JSON(), nullable=True, server_default="[]"))
    op.add_column("app_status_current", sa.Column("last_rating", sa.Float(), nullable=True))
    op.add_column("app_status_current", sa.Column("last_rating_count", sa.Integer(), nullable=True))
    op.add_column("app_status_current", sa.Column("last_price", sa.String(64), nullable=True))
    op.add_column("app_status_current", sa.Column("last_release_notes", sa.Text(), nullable=True))
    op.add_column("app_status_current", sa.Column("last_file_size", sa.String(64), nullable=True))
    op.add_column("app_status_current", sa.Column("last_content_rating", sa.String(64), nullable=True))
    op.add_column("app_status_current", sa.Column("last_store_updated_at", sa.String(64), nullable=True))


def downgrade() -> None:
    op.drop_column("app_status_current", "last_store_updated_at")
    op.drop_column("app_status_current", "last_content_rating")
    op.drop_column("app_status_current", "last_file_size")
    op.drop_column("app_status_current", "last_release_notes")
    op.drop_column("app_status_current", "last_price")
    op.drop_column("app_status_current", "last_rating_count")
    op.drop_column("app_status_current", "last_rating")
    op.drop_column("watched_apps", "tags")
