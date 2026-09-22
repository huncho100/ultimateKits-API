"""
Stock availability and consumption.

Stock is optional per product. A product whose
stock_quantity is NULL is not counted at all: its
availability is decided by the in_stock flag, exactly as it
was before quantities existed. A product with a number has
that number enforced.

Keeping both is deliberate. Backfilling every existing
product with a guessed opening quantity would have invented
a business fact; leaving them uncounted changes nothing
until an operator supplies real figures.
"""

import logging

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.order import Order
from app.models.product import Product


logger = logging.getLogger(__name__)


class InventoryService:
    """
    Answers what can be sold, and takes it off the shelf.
    """

    # ==========================================
    # Available Quantity
    # ==========================================

    @staticmethod
    def available_quantity(
        product: Product,
    ) -> int | None:
        """
        How many units of a product may be sold right now.

        Returns None when the product is not counted, which
        callers must read as "no quantity limit", not as
        zero.
        """

        if not product.in_stock:
            return 0

        if product.stock_quantity is None:
            return None

        return max(product.stock_quantity, 0)

    # ==========================================
    # Check Availability
    # ==========================================

    @staticmethod
    def assert_available(
        product: Product,
        quantity: int,
    ) -> None:
        """
        Refuse a quantity the shelf cannot supply.

        Raises HTTPException so that cart and order callers
        surface the same message.
        """

        available = InventoryService.available_quantity(
            product,
        )

        if available == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Product is out of stock.",
            )

        if available is not None and quantity > available:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Only {available} left in stock for "
                    f"{product.name}."
                ),
            )

    # ==========================================
    # Consume Stock
    # ==========================================

    @staticmethod
    def consume_for_order(
        db: Session,
        order: Order,
    ) -> None:
        """
        Take an order's items off the shelf.

        Called once, when the order becomes paid. Rows are
        locked before they are read so two checkouts settling
        at the same instant cannot both read the last unit
        and both decide it is theirs. The lock is taken in a
        fixed id order, because two transactions grabbing the
        same two products in opposite orders deadlock.

        SQLite ignores row locking, so the tests exercise the
        arithmetic rather than the concurrency. The guarantee
        is only real on PostgreSQL.

        This does not raise. By the time it runs the customer
        has already been charged, so refusing the order would
        leave them paid-for-nothing. A shortfall is clamped
        at zero and logged for an operator to resolve.
        """

        quantities: dict[int, int] = {}

        for item in order.items:
            quantities[item.product_id] = (
                quantities.get(item.product_id, 0)
                + item.quantity
            )

        if not quantities:
            return

        products = (
            db.query(Product)
            .filter(Product.id.in_(quantities))
            .order_by(Product.id)
            .with_for_update()
            .all()
        )

        for product in products:
            if product.stock_quantity is None:
                continue

            wanted = quantities[product.id]

            remaining = product.stock_quantity - wanted

            if remaining < 0:
                logger.critical(
                    "Oversold product %s on order %s: %s "
                    "requested, %s in stock. The order is "
                    "honoured; stock needs correcting.",
                    product.id,
                    order.id,
                    wanted,
                    product.stock_quantity,
                )

                remaining = 0

            product.stock_quantity = remaining

            if remaining == 0:
                product.in_stock = False
