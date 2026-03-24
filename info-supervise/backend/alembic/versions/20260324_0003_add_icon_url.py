"""add last_icon_url to app_status_current"""

from alembic import op
import sqlalchemy as sa

revision = "20260324_0003"
down_revision = "20260324_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "app_status_current",
        sa.Column("last_icon_url", sa.String(1000), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("app_status_current", "last_icon_url")
