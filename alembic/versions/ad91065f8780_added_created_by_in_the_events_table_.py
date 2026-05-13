"""added created_by in the events table and events in the user table

Revision ID: ad91065f8780
Revises: d749e5292d54
Create Date: 2026-05-13 11:15:37.070331
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "ad91065f8780"
down_revision: Union[str, Sequence[str], None] = "d749e5292d54"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add column as nullable
    op.add_column("events", sa.Column("created_by", sa.Integer(), nullable=True))

    # 2. Add foreign key HERE
    op.create_foreign_key(
        "fk_events_created_by_users",
        "events",
        "users",
        ["created_by"],
        ["id"],
    )

    # 3. Seed old rows
    op.execute("""
        UPDATE events
        SET created_by = 1
        WHERE created_by IS NULL
    """)

    # 4. Make NOT NULL
    op.alter_column("events", "created_by", nullable=False)


def downgrade() -> None:
    op.drop_constraint(
        "fk_events_created_by_users",
        "events",
        type_="foreignkey",
    )

    op.drop_column("events", "created_by")
