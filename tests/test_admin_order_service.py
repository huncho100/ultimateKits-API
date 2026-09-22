from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.models.order import Order
from app.models.user import User
from app.services.admin_order_service import (
    AdminOrderService,
)


# ==========================================
# Test Helpers
# ==========================================


def create_test_user(
    db: Session,
    email: str,
    role: str = "customer",
) -> User:
    user = User(
        first_name="Test",
        last_name="User",
        email=email,
        password_hash="test-password-hash",
        role=role,
        is_active=True,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def create_test_order(
    db: Session,
    user_id: int,
    status: str = "pending",
    total_amount: Decimal = Decimal("100.00"),
) -> Order:
    order = Order(
        user_id=user_id,
        status=status,
        total_amount=total_amount,
    )

    db.add(order)
    db.commit()
    db.refresh(order)

    return order


# ==========================================
# Get All Orders
# ==========================================


def test_get_all_orders(
    db: Session,
):
    user_one = create_test_user(
        db,
        "admin-order-user-1@example.com",
    )

    user_two = create_test_user(
        db,
        "admin-order-user-2@example.com",
    )

    first_order = create_test_order(
        db,
        user_one.id,
    )

    second_order = create_test_order(
        db,
        user_two.id,
    )

    orders = AdminOrderService.get_all_orders(db)

    order_ids = {order.id for order in orders}

    assert first_order.id in order_ids
    assert second_order.id in order_ids
    assert len(orders) == 2


# ==========================================
# Get Order By ID
# ==========================================


def test_get_order_by_id(
    db: Session,
):
    user = create_test_user(
        db,
        "admin-order-single@example.com",
    )

    order = create_test_order(
        db,
        user.id,
    )

    result = AdminOrderService.get_order_by_id(
        db,
        order.id,
    )

    assert result is not None
    assert result.id == order.id
    assert result.user_id == user.id


# ==========================================
# Get Nonexistent Order
# ==========================================


def test_get_nonexistent_order(
    db: Session,
):
    result = AdminOrderService.get_order_by_id(
        db,
        999999,
    )

    assert result is None


# ==========================================
# Update Order Status
# ==========================================


@pytest.mark.parametrize(
    ("start_status", "new_status"),
    [
        ("paid", "processing"),
        ("processing", "shipped"),
        ("shipped", "delivered"),
        ("pending", "cancelled"),
        ("paid", "cancelled"),
        ("processing", "cancelled"),
    ],
)
def test_update_order_status(
    db: Session,
    start_status: str,
    new_status: str,
):
    """
    Every status an administrator owns can be reached from
    the status that legitimately precedes it.
    """

    user = create_test_user(
        db,
        f"status-{start_status}-{new_status}@example.com",
    )

    order = create_test_order(
        db,
        user.id,
        status=start_status,
    )

    result = AdminOrderService.update_order_status(
        db,
        order,
        new_status,
    )

    assert result.status == new_status


# ==========================================
# Payment-Controlled Statuses
# ==========================================


@pytest.mark.parametrize(
    "payment_status",
    [
        "pending",
        "paid",
        "payment_failed",
    ],
)
def test_update_order_status_rejects_payment_statuses(
    db: Session,
    payment_status: str,
):
    """
    An administrator must not be able to type an order into
    "paid". Payment states record what the provider told us,
    so allowing them here would let an order be marked paid
    without any money having moved.
    """

    user = create_test_user(
        db,
        f"payment-status-{payment_status}@example.com",
    )

    order = create_test_order(
        db,
        user.id,
        status="processing",
    )

    with pytest.raises(
        ValueError,
        match="set by the payment process",
    ):
        AdminOrderService.update_order_status(
            db,
            order,
            payment_status,
        )

    assert order.status == "processing"


# ==========================================
# Illegal Transitions
# ==========================================


@pytest.mark.parametrize(
    ("start_status", "new_status"),
    [
        # Fulfilment cannot begin before payment.
        ("pending", "processing"),
        ("payment_failed", "shipped"),
        # Steps cannot be skipped.
        ("paid", "shipped"),
        ("paid", "delivered"),
        ("processing", "delivered"),
        # Finished orders stay finished.
        ("delivered", "processing"),
        ("cancelled", "processing"),
        # Goods that have left are a return, which this
        # system does not model.
        ("shipped", "cancelled"),
    ],
)
def test_update_order_status_rejects_illegal_transition(
    db: Session,
    start_status: str,
    new_status: str,
):
    user = create_test_user(
        db,
        f"illegal-{start_status}-{new_status}@example.com",
    )

    order = create_test_order(
        db,
        user.id,
        status=start_status,
    )

    with pytest.raises(
        ValueError,
        match="cannot move from",
    ):
        AdminOrderService.update_order_status(
            db,
            order,
            new_status,
        )

    assert order.status == start_status


# ==========================================
# Repeating A Status
# ==========================================


def test_update_order_status_allows_repeat(
    db: Session,
):
    """
    A second click on the same button is not an error.
    """

    user = create_test_user(
        db,
        "status-repeat@example.com",
    )

    order = create_test_order(
        db,
        user.id,
        status="shipped",
    )

    result = AdminOrderService.update_order_status(
        db,
        order,
        "shipped",
    )

    assert result.status == "shipped"


# ==========================================
# Status Is Normalized
# ==========================================


def test_update_order_status_normalizes_value(
    db: Session,
):
    user = create_test_user(
        db,
        "status-normalization@example.com",
    )

    order = create_test_order(
        db,
        user.id,
        status="processing",
    )

    result = AdminOrderService.update_order_status(
        db,
        order,
        "  SHIPPED  ",
    )

    assert result.status == "shipped"


# ==========================================
# Invalid Status
# ==========================================


def test_update_order_status_rejects_invalid_status(
    db: Session,
):
    user = create_test_user(
        db,
        "invalid-status@example.com",
    )

    order = create_test_order(
        db,
        user.id,
        status="pending",
    )

    with pytest.raises(
        ValueError,
        match="Invalid order status",
    ):
        AdminOrderService.update_order_status(
            db,
            order,
            "invalid-status",
        )

    assert order.status == "pending"