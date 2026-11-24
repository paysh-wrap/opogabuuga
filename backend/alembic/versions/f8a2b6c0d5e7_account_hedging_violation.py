"""D182: accounts.hedging_violation (a Hedging Violation makes the account ineligible for on-demand payouts)

Revision ID: f8a2b6c0d5e7
Revises: e7f1a5b9c4d6
Create Date: 2026-11-24 18:00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f8a2b6c0d5e7"
down_revision: Union[str, Sequence[str], None] = "e7f1a5b9c4d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("accounts", schema=None) as batch_op:
        batch_op.add_column(sa.Column("hedging_violation", sa.Boolean(), nullable=False, server_default="0"))


def downgrade() -> None:
    with op.batch_alter_table("accounts", schema=None) as batch_op:
        batch_op.drop_column("hedging_violation")
