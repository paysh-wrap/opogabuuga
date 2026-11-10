"""restart recovery: trades.om_state + events.processed_at

Revision ID: b4c8d2e6f1a3
Revises: 9c1e5a7b2d40
Create Date: 2026-11-10 12:00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import app.db  # noqa: F401  (custom column types)

revision: str = "b4c8d2e6f1a3"
down_revision: Union[str, Sequence[str], None] = "9c1e5a7b2d40"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("trades", schema=None) as batch_op:
        batch_op.add_column(sa.Column("om_state", sa.JSON(), nullable=True))
    with op.batch_alter_table("events", schema=None) as batch_op:
        batch_op.add_column(sa.Column("processed_at", app.db.UTCDateTime(), nullable=True))
        batch_op.create_index("ix_events_processed_at", ["processed_at"], unique=False)
    # history is not reprocessed: every existing event counts as processed
    op.execute("UPDATE events SET processed_at = created_at WHERE processed_at IS NULL")


def downgrade() -> None:
    with op.batch_alter_table("events", schema=None) as batch_op:
        batch_op.drop_index("ix_events_processed_at")
        batch_op.drop_column("processed_at")
    with op.batch_alter_table("trades", schema=None) as batch_op:
        batch_op.drop_column("om_state")
