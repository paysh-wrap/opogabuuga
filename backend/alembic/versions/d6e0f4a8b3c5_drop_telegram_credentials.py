"""D90: Telegram removed - delete any stored Telegram credential (Discord stays)

Revision ID: d6e0f4a8b3c5
Revises: c5d9e3f7a2b4
Create Date: 2026-11-11 13:00:00

"""

from typing import Sequence, Union

from alembic import op

revision: str = "d6e0f4a8b3c5"
down_revision: Union[str, Sequence[str], None] = "c5d9e3f7a2b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DELETE FROM api_credentials WHERE provider = 'telegram'")


def downgrade() -> None:
    pass  # a deleted credential cannot be restored (and was write-only anyway)
