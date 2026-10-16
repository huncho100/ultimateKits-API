"""add product image gallery

Revision ID: a52c7e9d4b61
Revises: f24c8d6a901b
Create Date: 2026-10-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "a52c7e9d4b61"
down_revision: Union[str, Sequence[str], None] = "f24c8d6a901b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    products = sa.table(
        "products",
        sa.column("name", sa.String()),
        sa.column("image", sa.String()),
    )
    op.execute(
        products.update()
        .where(
            products.c.name == "Chelsea Home Jersey",
            products.c.image
            == "/images/products/football/chelsea-home.webp",
        )
        .values(
            image="/images/products/football/chelsea-home-front.webp"
        )
    )

    op.create_table(
        "product_images",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "product_id",
            sa.Integer(),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("image_url", sa.String(length=500), nullable=False),
        sa.Column(
            "sort_order",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "is_primary",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "image_url LIKE '/images/products/%'",
            name="ck_product_images_public_path",
        ),
        sa.UniqueConstraint(
            "product_id",
            "image_url",
            name="uq_product_images_product_url",
        ),
    )
    op.create_index(
        "ix_product_images_product_id",
        "product_images",
        ["product_id"],
    )
    op.create_index(
        "uq_product_images_one_primary",
        "product_images",
        ["product_id"],
        unique=True,
        postgresql_where=sa.text("is_primary IS TRUE"),
        sqlite_where=sa.text("is_primary = 1"),
    )
    op.execute(
        sa.text(
            "INSERT INTO product_images "
            "(product_id, image_url, sort_order, is_primary) "
            "SELECT id, image, 0, TRUE FROM products "
            "WHERE image IS NOT NULL"
        )
    )


def downgrade() -> None:
    op.drop_index(
        "uq_product_images_one_primary",
        table_name="product_images",
    )
    op.drop_index(
        "ix_product_images_product_id",
        table_name="product_images",
    )
    op.drop_table("product_images")
