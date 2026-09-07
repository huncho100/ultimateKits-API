from sqlalchemy.orm import Session

from app.models.order import Order


# ==========================================
# Valid Order Statuses
# ==========================================

VALID_ORDER_STATUSES = {
    "pending",
    "processing",
    "shipped",
    "delivered",
    "cancelled",
}


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

        Only recognized order statuses are accepted.
        """

        normalized_status = status.strip().lower()

        if normalized_status not in VALID_ORDER_STATUSES:
            raise ValueError(
                f"Invalid order status: {status}"
            )

        order.status = normalized_status

        db.commit()
        db.refresh(order)

        return order