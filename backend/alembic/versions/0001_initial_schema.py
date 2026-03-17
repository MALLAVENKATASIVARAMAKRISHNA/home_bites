"""Initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2025-03-05 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("user_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("phone_number", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("city", sa.String(length=120), nullable=True),
        sa.CheckConstraint("role IN ('admin', 'user')", name="ck_users_role"),
        sa.PrimaryKeyConstraint("user_id"),
        sa.UniqueConstraint("phone_number"),
    )
    op.create_table(
        "items",
        sa.Column("item_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("item_name", sa.String(length=255), nullable=False),
        sa.Column("price", sa.Integer(), nullable=False),
        sa.Column("weight", sa.String(length=120), nullable=False),
        sa.Column("photos", sa.Text(), nullable=True),
        sa.Column("videos", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("item_id"),
    )
    op.create_table(
        "orders",
        sa.Column("order_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("order_status", sa.String(length=20), nullable=False),
        sa.Column("payment_status", sa.String(length=20), nullable=False),
        sa.Column("payment_mode", sa.String(length=20), nullable=False),
        sa.Column("order_date", sa.String(length=20), nullable=False),
        sa.Column("delivery_date", sa.String(length=20), nullable=True),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("city", sa.String(length=120), nullable=False),
        sa.CheckConstraint(
            "order_status IN ('pending','confirmed','delivered','cancelled')",
            name="ck_orders_order_status",
        ),
        sa.CheckConstraint(
            "payment_status IN ('pending','paid','failed')",
            name="ck_orders_payment_status",
        ),
        sa.CheckConstraint(
            "payment_mode IN ('cash','upi','card')",
            name="ck_orders_payment_mode",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"]),
        sa.PrimaryKeyConstraint("order_id"),
    )
    op.create_table(
        "order_details",
        sa.Column("order_detail_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("price", sa.Integer(), nullable=False),
        sa.CheckConstraint("price >= 0", name="ck_order_details_price_nonnegative"),
        sa.CheckConstraint("quantity > 0", name="ck_order_details_quantity_positive"),
        sa.ForeignKeyConstraint(["item_id"], ["items.item_id"]),
        sa.ForeignKeyConstraint(["order_id"], ["orders.order_id"]),
        sa.PrimaryKeyConstraint("order_detail_id"),
    )


def downgrade() -> None:
    op.drop_table("order_details")
    op.drop_table("orders")
    op.drop_table("items")
    op.drop_table("users")
