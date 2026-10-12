"""correct Chelsea and Manchester United primary image paths

Revision ID: f24c8d6a901b
Revises: e91f6a2c4b10
Create Date: 2026-10-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "f24c8d6a901b"
down_revision: Union[str, Sequence[str], None] = "e91f6a2c4b10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    products = sa.table(
        "products",
        sa.column("name", sa.String()),
        sa.column("image", sa.String()),
    )
    for name, filename in (
        ("Manchester United Home Jersey", "manchester-united-home"),
        ("Chelsea Home Jersey", "chelsea-home"),
    ):
        op.execute(
            products.update()
            .where(
                products.c.name == name,
                products.c.image.in_(
                    (
                        f"/images/{filename}.jpg",
                        f"/images/products/football/{filename}.jpg",
                    )
                ),
            )
            .values(image=f"/images/products/football/{filename}.webp")
        )


def downgrade() -> None:
    # Do not restore paths to files that no longer exist.
    pass
