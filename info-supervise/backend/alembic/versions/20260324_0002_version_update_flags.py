"""add version update notification flags"""

from alembic import op
import sqlalchemy as sa

revision = "20260324_0002"
down_revision = "20260324_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "watched_apps",
        sa.Column(
            "notify_on_version_update",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.add_column(
        "watched_publishers",
        sa.Column(
            "auto_added_notify_on_version_update",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )


def downgrade() -> None:
    op.drop_column("watched_publishers", "auto_added_notify_on_version_update")
    op.drop_column("watched_apps", "notify_on_version_update")
