from typing import Final


# ==========================================
# Order Status Vocabulary
# ==========================================

class OrderStatus:
    """
    The single vocabulary for Order.status.

    Before this existed the payment code wrote "paid" and
    "payment_failed" while the administration code only
    recognised "pending", "processing", "shipped",
    "delivered" and "cancelled". The two sets overlapped on
    one value, so a paid order could not be advanced without
    an administrator first overwriting the record of payment.
    """

    # Set when the order is created, before any payment.
    PENDING: Final = "pending"

    # Written only by the payment settlement path.
    PAID: Final = "paid"
    PAYMENT_FAILED: Final = "payment_failed"

    # Fulfilment, driven by an administrator.
    PROCESSING: Final = "processing"
    SHIPPED: Final = "shipped"
    DELIVERED: Final = "delivered"
    CANCELLED: Final = "cancelled"


ORDER_STATUSES: Final = frozenset(
    {
        OrderStatus.PENDING,
        OrderStatus.PAID,
        OrderStatus.PAYMENT_FAILED,
        OrderStatus.PROCESSING,
        OrderStatus.SHIPPED,
        OrderStatus.DELIVERED,
        OrderStatus.CANCELLED,
    }
)


# Statuses that record what the payment provider told us.
# An administrator must not be able to type these in: doing
# so would let an order be marked paid without any money
# having moved.
PAYMENT_CONTROLLED_STATUSES: Final = frozenset(
    {
        OrderStatus.PENDING,
        OrderStatus.PAID,
        OrderStatus.PAYMENT_FAILED,
    }
)


ADMIN_SETTABLE_STATUSES: Final = frozenset(
    ORDER_STATUSES - PAYMENT_CONTROLLED_STATUSES
)


# ==========================================
# Transitions
# ==========================================

# What each status may become. Anything absent is terminal.
#
# Deliberately absent, and worth stating explicitly:
#
# - Nothing returns to "pending". An order that has been
#   paid for cannot be made unpaid by changing a string.
# - "shipped" cannot be cancelled. Once goods have left,
#   the process is a return, which this system does not
#   model. Flagged rather than invented.
# - "delivered" and "cancelled" are final.
#
# Cancelling a paid order is permitted because an operator
# genuinely needs to, but no refund is issued by this
# system: that is currently a manual step in the Paystack
# dashboard.
ORDER_STATUS_TRANSITIONS: Final[dict[str, frozenset[str]]] = {
    OrderStatus.PENDING: frozenset(
        {
            OrderStatus.PAID,
            OrderStatus.PAYMENT_FAILED,
            OrderStatus.CANCELLED,
        }
    ),
    OrderStatus.PAYMENT_FAILED: frozenset(
        {
            OrderStatus.PAID,
            OrderStatus.CANCELLED,
        }
    ),
    OrderStatus.PAID: frozenset(
        {
            OrderStatus.PROCESSING,
            OrderStatus.CANCELLED,
        }
    ),
    OrderStatus.PROCESSING: frozenset(
        {
            OrderStatus.SHIPPED,
            OrderStatus.CANCELLED,
        }
    ),
    OrderStatus.SHIPPED: frozenset(
        {
            OrderStatus.DELIVERED,
        }
    ),
    OrderStatus.DELIVERED: frozenset(),
    OrderStatus.CANCELLED: frozenset(),
}


# ==========================================
# Payment Status Vocabulary
# ==========================================

class PaymentStatus:
    """
    The single vocabulary for Payment.status.

    "pending", "success" and "failed" mirror what Paystack
    reports. "abandoned" is ours alone: it marks a reference
    the customer was given but then replaced by starting
    checkout again, so it is not waiting on anything.
    """

    PENDING: Final = "pending"
    SUCCESS: Final = "success"
    FAILED: Final = "failed"
    ABANDONED: Final = "abandoned"


def can_transition(
    current_status: str,
    target_status: str,
) -> bool:
    """
    Report whether an order may move from one status to
    another.

    Re-applying the status an order already holds is allowed
    and does nothing, so a duplicate provider event or a
    repeated administrator click is harmless.
    """

    if current_status == target_status:
        return True

    return target_status in ORDER_STATUS_TRANSITIONS.get(
        current_status,
        frozenset(),
    )
