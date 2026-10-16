"""Track stable seed identity and development-only price provenance."""

from alembic import op
import sqlalchemy as sa


revision = "b62f0d8e3c14"
down_revision = "a52c7e9d4b61"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("products", sa.Column("catalog_key", sa.String(255), nullable=True))
    op.create_index("uq_products_catalog_key", "products", ["catalog_key"], unique=True)
    op.add_column(
        "products",
        sa.Column(
            "development_placeholder", sa.Boolean(),
            nullable=False, server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("products", "development_placeholder")
    op.drop_index("uq_products_catalog_key", table_name="products")
    op.drop_column("products", "catalog_key")
