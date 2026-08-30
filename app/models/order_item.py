from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.database import Base


class OrderItem(Base):
    __tablename__ = "order_items"

    # ==========================================
    # Primary Key
    # ==========================================

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    # ==========================================
    # Order
    # ==========================================

    order_id: Mapped[int] = mapped_column(
        ForeignKey(
            "orders.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # ==========================================
    # Product
    # ==========================================

    product_id: Mapped[int] = mapped_column(
        ForeignKey(
            "products.id",
        ),
        nullable=False,
        index=True,
    )

    # ==========================================
    # Quantity
    # ==========================================

    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # ==========================================
    # Price Snapshot
    # ==========================================

    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    # ==========================================
    # Item Subtotal
    # ==========================================

    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    # ==========================================
    # Relationships
    # ==========================================

    order = relationship(
        "Order",
        back_populates="items",
    )

    product = relationship(
        "Product",
        back_populates="order_items",
    )