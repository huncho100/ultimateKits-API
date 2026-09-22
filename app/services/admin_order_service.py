from sqlalchemy.orm import Session

from app.core.statuses import (
    ADMIN_SETTABLE_STATUSES,
    ORDER_STATUSES,
    can_transition,
)
from app.models.order import Order


# ==========================================
# Valid Order Statuses
# ==========================================

# Kept as a name because callers and tests refer to it, but
# the vocabulary itself now lives in app.core.statuses so
# the payment code and the administration code cannot drift
# apart again.
VALID_ORDER_STATUSES = ADMIN_SETTABLE_STATUSES


# ==========================================
# Admin Order Service
# ==========================================


class AdminOrderService:
    """
    Handles administrator-specific order
    management operations.
    """

    # ==========================================
    # Get All Orders
    # ==========================================

    @staticmethod
    def get_all_orders(
        db: Session,
    ) -> list[Order]:
        """
        Retrieve all orders.

        Orders are returned newest first.
        """

        return (
            db.query(Order)
            .order_by(Order.created_at.desc())
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
        Retrieve any order by its ID.

        Unlike the customer-facing order service,
        this method does not restrict the order
        to a particular user.
        """

        return (
            db.query(Order)
            .filter(Order.id == order_id)
            .first()
        )

    # ==========================================
    # Update Order Status
    # ==========================================

    @staticmethod
    def update_order_status(
        db: Session,
        order: Order,
        status: str,
    ) -> Order:
        """
        Update an order's status.

        Three separate rules apply:

        1. The value has to be a status this system knows.
        2. It has to be one an administrator owns. Payment
           outcomes are recorded by the settlement path, so
           an order cannot be typed into "paid".
        3. The move has to be legal from where the order is
           now, which is what stops a delivered order being
           dragged back to processing.
        """

        normalized_status = status.strip().lower()

        if normalized_status not in ORDER_STATUSES:
            raise ValueError(
                f"Invalid order status: {status}"
            )

        if normalized_status not in ADMIN_SETTABLE_STATUSES:
            raise ValueError(
                f"Order status '{normalized_status}' is set "
                "by the payment process and cannot be "
                "changed manually."
            )

        if not can_transition(
            order.status,
            normalized_status,
        ):
            raise ValueError(
                f"An order cannot move from "
                f"'{order.status}' to "
                f"'{normalized_status}'."
            )

        order.status = normalized_status

        db.commit()
        db.refresh(order)

        return order