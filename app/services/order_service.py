from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.statuses import OrderStatus
from app.models.cart import Cart
from app.models.order import Order
from app.models.order_item import OrderItem
from app.services.inventory_service import InventoryService


def _order_signature(
    items: list[OrderItem],
) -> frozenset[tuple[int, int, Decimal]]:
    """
    Summarise what an order is for, so two orders placed
    from the same unchanged cart can be recognised as the
    same order.
    """

    return frozenset(
        (
            item.product_id,
            item.quantity,
            Decimal(item.unit_price),
        )
        for item in items
    )


class OrderService:
    # ==========================================
    # Create Order From Cart
    # ==========================================

    @staticmethod
    def create_order_from_cart(
        db: Session,
        user_id: int,
    ) -> Order:
        """
        Create an order from the user's cart.

        The current cart items are converted into
        order items. Product prices are copied into
        the order as price snapshots.

        The cart is deliberately left intact. It is emptied
        when the order is actually paid for, so a customer
        whose card is declined still has something to retry
        with.

        Placing the same unchanged cart twice returns the
        order already waiting for payment rather than
        creating a second one.
        """

        # ------------------------------------------
        # Get User Cart
        # ------------------------------------------

        cart = (
            db.query(Cart)
            .filter(
                Cart.user_id == user_id,
            )
            .first()
        )

        # ------------------------------------------
        # Cart Does Not Exist / Empty Cart
        # ------------------------------------------

        if cart is None or not cart.items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot create an order from an empty cart.",
            )

        # ------------------------------------------
        # Validate Products
        # ------------------------------------------

        for cart_item in cart.items:
            product = cart_item.product

            if product is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Product not found.",
                )

            InventoryService.assert_available(
                product,
                cart_item.quantity,
            )

        # ------------------------------------------
        # Reuse An Unpaid Order For The Same Cart
        # ------------------------------------------

        # A double-submitted checkout, or a customer going
        # back and pressing the button again, must not leave
        # a trail of orders the customer never meant to
        # place. Prices are part of the comparison, so a
        # repriced cart still produces a new order.

        requested = frozenset(
            (
                cart_item.product_id,
                cart_item.quantity,
                Decimal(cart_item.product.price),
            )
            for cart_item in cart.items
        )

        pending_orders = (
            db.query(Order)
            .filter(
                Order.user_id == user_id,
                Order.status == OrderStatus.PENDING,
            )
            .all()
        )

        for existing in pending_orders:
            if _order_signature(existing.items) == requested:
                return existing

        # ------------------------------------------
        # Create Order
        # ------------------------------------------

        order = Order(
            user_id=user_id,
            status=OrderStatus.PENDING,
            total_amount=Decimal("0.00"),
        )

        db.add(order)
        db.flush()

        # ------------------------------------------
        # Create Order Items
        # ------------------------------------------

        total_amount = Decimal("0.00")

        for cart_item in cart.items:
            product = cart_item.product

            unit_price = product.price

            subtotal = (
                unit_price
                * cart_item.quantity
            ).quantize(
                Decimal("0.01")
            )

            order_item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=cart_item.quantity,
                unit_price=unit_price,
                subtotal=subtotal,
            )

            db.add(order_item)

            total_amount += subtotal

        # ------------------------------------------
        # Set Order Total
        # ------------------------------------------

        order.total_amount = total_amount.quantize(
            Decimal("0.01")
        )

        # ------------------------------------------
        # Save Order
        # ------------------------------------------

        db.commit()
        db.refresh(order)

        return order

    # ==========================================
    # Get User Orders
    # ==========================================

    @staticmethod
    def get_user_orders(
        db: Session,
        user_id: int,
    ) -> list[Order]:
        """
        Retrieve all orders belonging to a user.
        """

        return (
            db.query(Order)
            .filter(
                Order.user_id == user_id,
            )
            .order_by(
                Order.created_at.desc(),
            )
            .all()
        )

    # ==========================================
    # Get Order By ID
    # ==========================================

    @staticmethod
    def get_order_by_id(
        db: Session,
        order_id: int,
    ) -> Order | None:
        """
        Retrieve an order by its ID.
        """

        return (
            db.query(Order)
            .filter(
                Order.id == order_id,
            )
            .first()
        )