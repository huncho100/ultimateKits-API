"""add password_changed_at to users

Revision ID: b3f1c9a27d04
Revises: 6666f5d1581a
Create Date: 2026-09-21 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision: str = 'b3f1c9a27d04'
down_revision: Union[str, Sequence[str], None] = '6666f5d1581a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Nullable with no server default, so the column can be
    # added to a populated table without a rewrite or a lock
    # held for the length of a backfill.
    #
    # NULL means "the password has never been changed", which
    # is the correct starting state for existing rows: their
    # tokens are not retroactively invalidated.
    op.add_column(
        'users',
        sa.Column(
            'password_changed_at',
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'password_changed_at')
