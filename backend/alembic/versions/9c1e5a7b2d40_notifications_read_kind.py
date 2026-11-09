"""notifications: kind + read_at (in-app alerts bell)

Revision ID: 9c1e5a7b2d40
Revises: 55474a0116dd
Create Date: 2026-11-06 08:00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import app.db  # noqa: F401  (custom column types)

revision: str = "9c1e5a7b2d40"
down_revision: Union[str, Sequence[str], None] = "55474a0116dd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("notifications", schema=None) as batch_op:
        batch_op.add_column(sa.Column("kind", sa.String(length=32), server_default="general", nullable=False))
        batch_op.add_column(sa.Column("read_at", app.db.UTCDateTime(), nullable=True))
        batch_op.create_index("ix_notifications_read_at", ["read_at"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("notifications", schema=None) as batch_op:
        batch_op.drop_index("ix_notifications_read_at")
        batch_op.drop_column("read_at")
        batch_op.drop_column("kind")
