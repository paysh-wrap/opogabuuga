"""D89: accounts.purchased_at (when the Lucid account was purchased / last reset)

Revision ID: c5d9e3f7a2b4
Revises: b4c8d2e6f1a3
Create Date: 2026-11-11 12:00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import app.db  # noqa: F401  (custom column types)

revision: str = "c5d9e3f7a2b4"
down_revision: Union[str, Sequence[str], None] = "b4c8d2e6f1a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("accounts", schema=None) as batch_op:
        batch_op.add_column(sa.Column("purchased_at", app.db.UTCDateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("accounts", schema=None) as batch_op:
        batch_op.drop_column("purchased_at")
