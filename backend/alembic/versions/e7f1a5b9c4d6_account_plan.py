"""D168: accounts.plan (rule plan file stem per account; NULL = inferred from the account size)

Revision ID: e7f1a5b9c4d6
Revises: d6e0f4a8b3c5
Create Date: 2026-11-24 12:00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e7f1a5b9c4d6"
down_revision: Union[str, Sequence[str], None] = "d6e0f4a8b3c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("accounts", schema=None) as batch_op:
        batch_op.add_column(sa.Column("plan", sa.String(length=64), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("accounts", schema=None) as batch_op:
        batch_op.drop_column("plan")
