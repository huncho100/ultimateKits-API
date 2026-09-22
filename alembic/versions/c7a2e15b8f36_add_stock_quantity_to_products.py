"""add stock_quantity to products

Revision ID: c7a2e15b8f36
Revises: b3f1c9a27d04
Create Date: 2026-09-21

Adds optional quantity tracking to products.

The column is nullable and is deliberately left NULL for
every existing row. NULL means "not counted", which is
exactly how products behaved before this column existed, so
the migration changes no behaviour on its own. An operator
turns counting on for a product by giving it a number.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "c7a2e15b8f36"
down_revision: Union[str, Sequence[str], None] = (
    "b3f1c9a27d04"
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column(
            "stock_quantity",
            sa.Integer(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column(
        "products",
        "stock_quantity",
    )
