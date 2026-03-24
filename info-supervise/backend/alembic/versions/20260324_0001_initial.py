"""initial schema"""

from alembic import op
import sqlalchemy as sa

revision = "20260324_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "watched_apps",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("store", sa.String(length=32), nullable=False),
        sa.Column("package_name", sa.String(length=255), nullable=True),
        sa.Column("bundle_id", sa.String(length=255), nullable=True),
        sa.Column("app_id", sa.String(length=64), nullable=True),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("regions", sa.JSON(), nullable=False),
        sa.Column("monitoring_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("auto_added", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("check_interval_minutes", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_watched_apps_store", "watched_apps", ["store"])
    op.create_index("ix_watched_apps_package_name", "watched_apps", ["package_name"])
    op.create_index("ix_watched_apps_bundle_id", "watched_apps", ["bundle_id"])
    op.create_index("ix_watched_apps_app_id", "watched_apps", ["app_id"])

    op.create_table(
        "watched_publishers",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("store", sa.String(length=32), nullable=False),
        sa.Column("publisher_name", sa.String(length=255), nullable=False),
        sa.Column("publisher_ref", sa.String(length=255), nullable=True),
        sa.Column("publisher_url", sa.String(length=500), nullable=True),
        sa.Column("regions", sa.JSON(), nullable=False),
        sa.Column("monitoring_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("auto_add_apps", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_watched_publishers_store", "watched_publishers", ["store"])
    op.create_index("ix_watched_publishers_publisher_name", "watched_publishers", ["publisher_name"])

    op.create_table(
        "app_store_snapshots",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("watched_app_id", sa.String(length=36), sa.ForeignKey("watched_apps.id", ondelete="CASCADE"), nullable=False),
        sa.Column("store", sa.String(length=32), nullable=False),
        sa.Column("region", sa.String(length=16), nullable=False),
        sa.Column("is_visible", sa.Boolean(), nullable=True),
        sa.Column("fetch_status", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("developer_name", sa.String(length=255), nullable=True),
        sa.Column("version", sa.String(length=64), nullable=True),
        sa.Column("category", sa.String(length=128), nullable=True),
        sa.Column("url", sa.String(length=500), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_app_store_snapshots_watched_app_id", "app_store_snapshots", ["watched_app_id"])
    op.create_index("ix_app_store_snapshots_store", "app_store_snapshots", ["store"])
    op.create_index("ix_app_store_snapshots_region", "app_store_snapshots", ["region"])
    op.create_index("ix_app_store_snapshots_observed_at", "app_store_snapshots", ["observed_at"])

    op.create_table(
        "publisher_snapshots",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "watched_publisher_id",
            sa.String(length=36),
            sa.ForeignKey("watched_publishers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("store", sa.String(length=32), nullable=False),
        sa.Column("region", sa.String(length=16), nullable=False),
        sa.Column("app_keys", sa.JSON(), nullable=False),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_publisher_snapshots_watched_publisher_id", "publisher_snapshots", ["watched_publisher_id"])
    op.create_index("ix_publisher_snapshots_store", "publisher_snapshots", ["store"])
    op.create_index("ix_publisher_snapshots_region", "publisher_snapshots", ["region"])
    op.create_index("ix_publisher_snapshots_observed_at", "publisher_snapshots", ["observed_at"])

    op.create_table(
        "app_status_current",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("watched_app_id", sa.String(length=36), sa.ForeignKey("watched_apps.id", ondelete="CASCADE"), nullable=False),
        sa.Column("store", sa.String(length=32), nullable=False),
        sa.Column("visible_regions", sa.JSON(), nullable=False),
        sa.Column("invisible_regions", sa.JSON(), nullable=False),
        sa.Column("region_states", sa.JSON(), nullable=False),
        sa.Column("last_seen_visible_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_invisible_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_title", sa.String(length=255), nullable=True),
        sa.Column("last_developer_name", sa.String(length=255), nullable=True),
        sa.Column("last_version", sa.String(length=64), nullable=True),
        sa.Column("last_category", sa.String(length=128), nullable=True),
        sa.Column("last_url", sa.String(length=500), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("watched_app_id", name="uq_app_status_current_watched_app_id"),
    )
    op.create_index("ix_app_status_current_watched_app_id", "app_status_current", ["watched_app_id"])
    op.create_index("ix_app_status_current_store", "app_status_current", ["store"])

    op.create_table(
        "events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("store", sa.String(length=32), nullable=False),
        sa.Column("watched_app_id", sa.String(length=36), sa.ForeignKey("watched_apps.id", ondelete="SET NULL"), nullable=True),
        sa.Column(
            "watched_publisher_id",
            sa.String(length=36),
            sa.ForeignKey("watched_publishers.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("region", sa.String(length=16), nullable=True),
        sa.Column("dedupe_key", sa.String(length=255), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_events_event_type", "events", ["event_type"])
    op.create_index("ix_events_store", "events", ["store"])
    op.create_index("ix_events_region", "events", ["region"])
    op.create_index("ix_events_status", "events", ["status"])
    op.create_index("ix_events_dedupe_key", "events", ["dedupe_key"])
    op.create_index("ix_events_created_at", "events", ["created_at"])

    op.create_table(
        "notification_channels",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("channel_type", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("webhook_url", sa.String(length=1000), nullable=False),
        sa.Column("secret", sa.String(length=255), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("config_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_notification_channels_channel_type", "notification_channels", ["channel_type"])
    op.create_index("ix_notification_channels_name", "notification_channels", ["name"])

    op.create_table(
        "job_runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("job_name", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("detail_json", sa.JSON(), nullable=False),
        sa.Column("error_text", sa.Text(), nullable=True),
    )
    op.create_index("ix_job_runs_job_name", "job_runs", ["job_name"])
    op.create_index("ix_job_runs_status", "job_runs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_job_runs_status", table_name="job_runs")
    op.drop_index("ix_job_runs_job_name", table_name="job_runs")
    op.drop_table("job_runs")

    op.drop_index("ix_notification_channels_name", table_name="notification_channels")
    op.drop_index("ix_notification_channels_channel_type", table_name="notification_channels")
    op.drop_table("notification_channels")

    op.drop_index("ix_events_created_at", table_name="events")
    op.drop_index("ix_events_dedupe_key", table_name="events")
    op.drop_index("ix_events_status", table_name="events")
    op.drop_index("ix_events_region", table_name="events")
    op.drop_index("ix_events_store", table_name="events")
    op.drop_index("ix_events_event_type", table_name="events")
    op.drop_table("events")

    op.drop_index("ix_app_status_current_store", table_name="app_status_current")
    op.drop_index("ix_app_status_current_watched_app_id", table_name="app_status_current")
    op.drop_table("app_status_current")

    op.drop_index("ix_publisher_snapshots_observed_at", table_name="publisher_snapshots")
    op.drop_index("ix_publisher_snapshots_region", table_name="publisher_snapshots")
    op.drop_index("ix_publisher_snapshots_store", table_name="publisher_snapshots")
    op.drop_index("ix_publisher_snapshots_watched_publisher_id", table_name="publisher_snapshots")
    op.drop_table("publisher_snapshots")

    op.drop_index("ix_app_store_snapshots_observed_at", table_name="app_store_snapshots")
    op.drop_index("ix_app_store_snapshots_region", table_name="app_store_snapshots")
    op.drop_index("ix_app_store_snapshots_store", table_name="app_store_snapshots")
    op.drop_index("ix_app_store_snapshots_watched_app_id", table_name="app_store_snapshots")
    op.drop_table("app_store_snapshots")

    op.drop_index("ix_watched_publishers_publisher_name", table_name="watched_publishers")
    op.drop_index("ix_watched_publishers_store", table_name="watched_publishers")
    op.drop_table("watched_publishers")

    op.drop_index("ix_watched_apps_app_id", table_name="watched_apps")
    op.drop_index("ix_watched_apps_bundle_id", table_name="watched_apps")
    op.drop_index("ix_watched_apps_package_name", table_name="watched_apps")
    op.drop_index("ix_watched_apps_store", table_name="watched_apps")
    op.drop_table("watched_apps")
