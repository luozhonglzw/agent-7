"""Add dept_id to users and update role defaults.

Revision ID: 001_add_dept_id
Revises:
Create Date: 2026-07-09

Changes:
    - Add dept_id (UUID, nullable) column to users table
    - Add index ix_users_dept on dept_id
    - Change role default from 'viewer' to 'user'
    - Update existing 'viewer' roles to 'user' and 'editor' to 'manager'
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "001_add_dept_id"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply migration: add dept_id, update role defaults and existing data."""
    # Add dept_id column (nullable, no default — existing rows get NULL)
    op.add_column(
        "users",
        sa.Column(
            "dept_id",
            UUID(as_uuid=True),
            nullable=True,
            comment="Department UUID for dept-scoped permissions",
        ),
    )

    # Create index on dept_id
    op.create_index("ix_users_dept", "users", ["dept_id"])

    # Migrate existing role values:
    #   viewer -> user
    #   editor -> manager
    op.execute(
        "UPDATE users SET role = 'user' WHERE role = 'viewer'"
    )
    op.execute(
        "UPDATE users SET role = 'manager' WHERE role = 'editor'"
    )

    # Change the column default for future inserts
    op.alter_column(
        "users",
        "role",
        server_default="user",
        existing_type=sa.String(50),
        comment="User role: admin, manager, user",
    )


def downgrade() -> None:
    """Revert migration: remove dept_id, restore old role values."""
    # Revert role default
    op.alter_column(
        "users",
        "role",
        server_default="viewer",
        existing_type=sa.String(50),
        comment="User role: admin, editor, viewer",
    )

    # Revert role data
    op.execute(
        "UPDATE users SET role = 'editor' WHERE role = 'manager'"
    )
    op.execute(
        "UPDATE users SET role = 'viewer' WHERE role = 'user'"
    )

    # Drop dept_id index and column
    op.drop_index("ix_users_dept", table_name="users")
    op.drop_column("users", "dept_id")
