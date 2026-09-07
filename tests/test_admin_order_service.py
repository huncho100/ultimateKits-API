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
    "new_status",
    [
        "pending",
        "processing",
        "shipped",
        "delivered",
        "cancelled",
    ],
)
def test_update_order_status(
    db: Session,
    new_status: str,
):
    user = create_test_user(
        db,
        f"status-{new_status}@example.com",
    )

    order = create_test_order(
        db,
        user.id,
        status="pending",
    )

    result = AdminOrderService.update_order_status(
        db,
        order,
        new_status,
    )

    assert result.status == new_status


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