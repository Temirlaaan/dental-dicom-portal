"""Add VM pool table and vm fields to sessions.

Revision ID: 003_vm_pool
Revises:
Create Date: 2026-02-23
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers
revision = "003_vm_pool"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create vm_instances table
    op.create_table(
        "vm_instances",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("hostname", sa.String(), nullable=False, unique=True),
        sa.Column("ip_address", sa.String(), nullable=False, unique=True),
        sa.Column("rdp_port", sa.Integer(), nullable=False, server_default="3389"),
        sa.Column("winrm_port", sa.Integer(), nullable=False, server_default="5985"),
        sa.Column("status", sa.String(), nullable=False, server_default="ready", index=True),
        sa.Column("doctor_id", UUID(as_uuid=True), nullable=True),
        sa.Column("doctor_name", sa.String(), nullable=True),
        sa.Column("session_id", UUID(as_uuid=True), nullable=True),
        sa.Column("mounted_share", sa.String(), nullable=True),
        sa.Column("assigned_at", sa.DateTime(), nullable=True),
        sa.Column("last_health_check", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )

    # Add VM columns to sessions table
    op.add_column("sessions", sa.Column("vm_instance_id", UUID(as_uuid=True), nullable=True))
    op.add_column("sessions", sa.Column("vm_ip", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("sessions", "vm_ip")
    op.drop_column("sessions", "vm_instance_id")
    op.drop_table("vm_instances")
