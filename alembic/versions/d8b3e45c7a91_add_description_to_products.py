"""add description to products

Revision ID: d8b3e45c7a91
Revises: c7a2e15b8f36
Create Date: 2026-10-03

Adds an optional long-form description to products.

The column is nullable and is deliberately left NULL for
every existing row. NULL means "no description has been
published", which is exactly how products behaved before
this column existed, so the migration changes no behaviour
on its own. An administrator publishes a description by
writing one.

Nothing is backfilled. Descriptions are claims about goods
that only the seller can make truthfully, so inventing text
here would put words on the product page that nobody in the
business wrote. See docs/product-content.md.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "d8b3e45c7a91"
down_revision: Union[str, Sequence[str], None] = (
    "c7a2e15b8f36"
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column(
        "products",
        "description",
    )
