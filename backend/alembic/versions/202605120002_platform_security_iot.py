"""platform security and iot primitives

Revision ID: 202605120002
Revises: 202605120001
Create Date: 2026-05-12 14:20:00
"""

from alembic import op
import sqlalchemy as sa

revision = "202605120002"
down_revision = "202605120001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("role", sa.String(length=32), nullable=False, server_default="user"))
    op.add_column("devices", sa.Column("secret_hash", sa.String(length=255), nullable=True))

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_refresh_tokens_id"), "refresh_tokens", ["id"], unique=False)
    op.create_index(op.f("ix_refresh_tokens_token_hash"), "refresh_tokens", ["token_hash"], unique=True)
    op.create_index(op.f("ix_refresh_tokens_user_id"), "refresh_tokens", ["user_id"], unique=False)

    op.create_table(
        "idempotency_keys",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("scope", sa.String(length=64), nullable=False),
        sa.Column("request_hash", sa.String(length=128), nullable=False),
        sa.Column("response_body", sa.Text(), nullable=True),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_idempotency_keys_id"), "idempotency_keys", ["id"], unique=False)
    op.create_index(op.f("ix_idempotency_keys_key"), "idempotency_keys", ["key"], unique=True)
    op.create_index(op.f("ix_idempotency_keys_scope"), "idempotency_keys", ["scope"], unique=False)

    op.create_table(
        "outbox_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_name", sa.String(length=128), nullable=False),
        sa.Column("aggregate_type", sa.String(length=64), nullable=False),
        sa.Column("aggregate_id", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(), nullable=False),
        sa.Column("locked_at", sa.DateTime(), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_outbox_events_aggregate_id"), "outbox_events", ["aggregate_id"], unique=False)
    op.create_index(op.f("ix_outbox_events_aggregate_type"), "outbox_events", ["aggregate_type"], unique=False)
    op.create_index(op.f("ix_outbox_events_event_name"), "outbox_events", ["event_name"], unique=False)
    op.create_index(op.f("ix_outbox_events_id"), "outbox_events", ["id"], unique=False)
    op.create_index(op.f("ix_outbox_events_next_attempt_at"), "outbox_events", ["next_attempt_at"], unique=False)
    op.create_index(op.f("ix_outbox_events_status"), "outbox_events", ["status"], unique=False)

    op.create_table(
        "dead_letter_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_dead_letter_events_id"), "dead_letter_events", ["id"], unique=False)
    op.create_index(op.f("ix_dead_letter_events_source"), "dead_letter_events", ["source"], unique=False)

    op.create_table(
        "device_shadows",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("desired_state", sa.Text(), nullable=False),
        sa.Column("reported_state", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_device_shadows_device_id"), "device_shadows", ["device_id"], unique=True)
    op.create_index(op.f("ix_device_shadows_id"), "device_shadows", ["id"], unique=False)

    op.create_table(
        "device_commands",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("command", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("acked_at", sa.DateTime(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_device_commands_command"), "device_commands", ["command"], unique=False)
    op.create_index(op.f("ix_device_commands_device_id"), "device_commands", ["device_id"], unique=False)
    op.create_index(op.f("ix_device_commands_id"), "device_commands", ["id"], unique=False)
    op.create_index(op.f("ix_device_commands_idempotency_key"), "device_commands", ["idempotency_key"], unique=True)
    op.create_index(op.f("ix_device_commands_status"), "device_commands", ["status"], unique=False)

    op.create_table(
        "telemetry_points",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("metric", sa.String(length=64), nullable=False),
        sa.Column("value", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=True),
        sa.Column("recorded_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_telemetry_points_device_id"), "telemetry_points", ["device_id"], unique=False)
    op.create_index(op.f("ix_telemetry_points_id"), "telemetry_points", ["id"], unique=False)
    op.create_index(op.f("ix_telemetry_points_metric"), "telemetry_points", ["metric"], unique=False)
    op.create_index(op.f("ix_telemetry_points_recorded_at"), "telemetry_points", ["recorded_at"], unique=False)

    op.create_table(
        "rule_definitions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("metric", sa.String(length=64), nullable=False),
        sa.Column("operator", sa.String(length=16), nullable=False),
        sa.Column("threshold", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_rule_definitions_id"), "rule_definitions", ["id"], unique=False)
    op.create_index(op.f("ix_rule_definitions_metric"), "rule_definitions", ["metric"], unique=False)
    op.create_unique_constraint("uq_rule_definitions_name", "rule_definitions", ["name"])


def downgrade():
    op.drop_constraint("uq_rule_definitions_name", "rule_definitions", type_="unique")
    op.drop_index(op.f("ix_rule_definitions_metric"), table_name="rule_definitions")
    op.drop_index(op.f("ix_rule_definitions_id"), table_name="rule_definitions")
    op.drop_table("rule_definitions")
    op.drop_index(op.f("ix_telemetry_points_recorded_at"), table_name="telemetry_points")
    op.drop_index(op.f("ix_telemetry_points_metric"), table_name="telemetry_points")
    op.drop_index(op.f("ix_telemetry_points_id"), table_name="telemetry_points")
    op.drop_index(op.f("ix_telemetry_points_device_id"), table_name="telemetry_points")
    op.drop_table("telemetry_points")
    op.drop_index(op.f("ix_device_commands_status"), table_name="device_commands")
    op.drop_index(op.f("ix_device_commands_idempotency_key"), table_name="device_commands")
    op.drop_index(op.f("ix_device_commands_id"), table_name="device_commands")
    op.drop_index(op.f("ix_device_commands_device_id"), table_name="device_commands")
    op.drop_index(op.f("ix_device_commands_command"), table_name="device_commands")
    op.drop_table("device_commands")
    op.drop_index(op.f("ix_device_shadows_id"), table_name="device_shadows")
    op.drop_index(op.f("ix_device_shadows_device_id"), table_name="device_shadows")
    op.drop_table("device_shadows")
    op.drop_index(op.f("ix_dead_letter_events_source"), table_name="dead_letter_events")
    op.drop_index(op.f("ix_dead_letter_events_id"), table_name="dead_letter_events")
    op.drop_table("dead_letter_events")
    op.drop_index(op.f("ix_outbox_events_status"), table_name="outbox_events")
    op.drop_index(op.f("ix_outbox_events_next_attempt_at"), table_name="outbox_events")
    op.drop_index(op.f("ix_outbox_events_id"), table_name="outbox_events")
    op.drop_index(op.f("ix_outbox_events_event_name"), table_name="outbox_events")
    op.drop_index(op.f("ix_outbox_events_aggregate_type"), table_name="outbox_events")
    op.drop_index(op.f("ix_outbox_events_aggregate_id"), table_name="outbox_events")
    op.drop_table("outbox_events")
    op.drop_index(op.f("ix_idempotency_keys_scope"), table_name="idempotency_keys")
    op.drop_index(op.f("ix_idempotency_keys_key"), table_name="idempotency_keys")
    op.drop_index(op.f("ix_idempotency_keys_id"), table_name="idempotency_keys")
    op.drop_table("idempotency_keys")
    op.drop_index(op.f("ix_refresh_tokens_user_id"), table_name="refresh_tokens")
    op.drop_index(op.f("ix_refresh_tokens_token_hash"), table_name="refresh_tokens")
    op.drop_index(op.f("ix_refresh_tokens_id"), table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
    op.drop_column("devices", "secret_hash")
    op.drop_column("users", "role")
