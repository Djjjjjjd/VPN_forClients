"""Initial schema."""

from alembic import op
import sqlalchemy as sa


revision = "20260414_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("first_name", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("telegram_id"),
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"], unique=False)

    op.create_table(
        "plans",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("duration_days", sa.Integer(), nullable=False),
        sa.Column("price_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_plans_code", "plans", ["code"], unique=False)

    op.create_table(
        "servers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("host", sa.String(length=255), nullable=False),
        sa.Column("public_ip", sa.String(length=64), nullable=False),
        sa.Column("wg_subnet", sa.String(length=64), nullable=False),
        sa.Column("country_code", sa.String(length=8), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("max_clients", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("plan_id", sa.Integer(), sa.ForeignKey("plans.id"), nullable=False),
        sa.Column("server_id", sa.Integer(), sa.ForeignKey("servers.id"), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"], unique=False)
    op.create_index("ix_subscriptions_server_id", "subscriptions", ["server_id"], unique=False)

    op.create_table(
        "vpn_clients",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("subscription_id", sa.Integer(), sa.ForeignKey("subscriptions.id"), nullable=False),
        sa.Column("server_id", sa.Integer(), sa.ForeignKey("servers.id"), nullable=False),
        sa.Column("client_name", sa.String(length=128), nullable=False),
        sa.Column("client_ip", sa.String(length=64), nullable=False),
        sa.Column("public_key", sa.String(length=255), nullable=False),
        sa.Column("config_path", sa.String(length=512), nullable=False),
        sa.Column("qr_path", sa.String(length=512), nullable=True),
        sa.Column("is_revoked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("client_name"),
        sa.UniqueConstraint("client_ip"),
        sa.UniqueConstraint("subscription_id", "is_revoked", name="uq_vpn_clients_subscription_revoked"),
    )
    op.create_index("ix_vpn_clients_subscription_id", "vpn_clients", ["subscription_id"], unique=False)
    op.create_index("ix_vpn_clients_server_id", "vpn_clients", ["server_id"], unique=False)
    op.create_index("ix_vpn_clients_user_id", "vpn_clients", ["user_id"], unique=False)

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("external_payment_id", sa.String(length=128), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("idempotence_key", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_payload_json", sa.JSON(), nullable=False),
        sa.UniqueConstraint("external_payment_id"),
        sa.UniqueConstraint("idempotence_key"),
    )
    op.create_index("ix_payments_external_payment_id", "payments", ["external_payment_id"], unique=False)
    op.create_index("ix_payments_idempotence_key", "payments", ["idempotence_key"], unique=False)
    op.create_index("ix_payments_user_id", "payments", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_payments_user_id", table_name="payments")
    op.drop_index("ix_payments_idempotence_key", table_name="payments")
    op.drop_index("ix_payments_external_payment_id", table_name="payments")
    op.drop_table("payments")
    op.drop_index("ix_vpn_clients_user_id", table_name="vpn_clients")
    op.drop_index("ix_vpn_clients_server_id", table_name="vpn_clients")
    op.drop_index("ix_vpn_clients_subscription_id", table_name="vpn_clients")
    op.drop_table("vpn_clients")
    op.drop_index("ix_subscriptions_server_id", table_name="subscriptions")
    op.drop_index("ix_subscriptions_user_id", table_name="subscriptions")
    op.drop_table("subscriptions")
    op.drop_table("servers")
    op.drop_index("ix_plans_code", table_name="plans")
    op.drop_table("plans")
    op.drop_index("ix_users_telegram_id", table_name="users")
    op.drop_table("users")
