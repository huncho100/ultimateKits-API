from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.order import Order
from app.models.user import User
from app.utils.security import create_access_token


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


def auth_headers(user: User) -> dict:
    token = create_access_token(
        {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role,
        }
    )

    return {
        "Authorization": f"Bearer {token}",
    }


# ==========================================
# Get All Orders
# ==========================================


def test_admin_can_get_all_orders(
    client: TestClient,
    db: Session,
):
    admin = create_test_user(
        db,
        "admin-all-orders@example.com",
        role="admin",
    )

    customer_one = create_test_user(
        db,
        "admin-orders-customer-1@example.com",
    )

    customer_two = create_test_user(
        db,
        "admin-orders-customer-2@example.com",
    )

    order_one = create_test_order(
        db,
        customer_one.id,
        total_amount=Decimal("50.00"),
    )

    order_two = create_test_order(
        db,
        customer_two.id,
        total_amount=Decimal("75.00"),
    )

    response = client.get(
        "/admin/orders",
        headers=auth_headers(admin),
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 2

    returned_ids = {
        item["id"]
        for item in data
    }

    assert order_one.id in returned_ids
    assert order_two.id in returned_ids


# ==========================================
# Customer Cannot Get All Orders
# ==========================================


def test_customer_cannot_get_all_orders(
    client: TestClient,
    db: Session,
):
    customer = create_test_user(
        db,
        "customer-admin-orders@example.com",
    )

    response = client.get(
        "/admin/orders",
        headers=auth_headers(customer),
    )

    assert response.status_code == 403

    assert response.json()["detail"] == (
        "Administrator access required."
    )


# ==========================================
# Unauthenticated Cannot Get All Orders
# ==========================================


def test_unauthenticated_cannot_get_all_orders(
    client: TestClient,
):
    response = client.get(
        "/admin/orders",
    )

    assert response.status_code == 401


# ==========================================
# Admin Can Get Any Order
# ==========================================


def test_admin_can_get_any_order(
    client: TestClient,
    db: Session,
):
    admin = create_test_user(
        db,
        "admin-any-order@example.com",
        role="admin",
    )

    customer = create_test_user(
        db,
        "admin-any-order-customer@example.com",
    )

    order = create_test_order(
        db,
        customer.id,
        total_amount=Decimal("125.00"),
    )

    response = client.get(
        f"/admin/orders/{order.id}",
        headers=auth_headers(admin),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == order.id
    assert data["user_id"] == customer.id
    assert data["status"] == "pending"
    assert Decimal(str(data["total_amount"])) == Decimal(
        "125.00"
    )


# ==========================================
# Customer Cannot Get Another User's Order
# ==========================================


def test_customer_cannot_get_admin_order(
    client: TestClient,
    db: Session,
):
    customer = create_test_user(
        db,
        "customer-order-access@example.com",
    )

    another_customer = create_test_user(
        db,
        "another-order-customer@example.com",
    )

    order = create_test_order(
        db,
        another_customer.id,
    )

    response = client.get(
        f"/admin/orders/{order.id}",
        headers=auth_headers(customer),
    )

    assert response.status_code == 403

    assert response.json()["detail"] == (
        "Administrator access required."
    )


# ==========================================
# Unauthenticated Cannot Get Order
# ==========================================


def test_unauthenticated_cannot_get_admin_order(
    client: TestClient,
    db: Session,
):
    customer = create_test_user(
        db,
        "unauthenticated-order-customer@example.com",
    )

    order = create_test_order(
        db,
        customer.id,
    )

    response = client.get(
        f"/admin/orders/{order.id}",
    )

    assert response.status_code == 401


# ==========================================
# Admin Get Nonexistent Order
# ==========================================


def test_admin_get_nonexistent_order(
    client: TestClient,
    db: Session,
):
    admin = create_test_user(
        db,
        "admin-nonexistent-order@example.com",
        role="admin",
    )

    response = client.get(
        "/admin/orders/999999",
        headers=auth_headers(admin),
    )

    assert response.status_code == 404

    assert response.json()["detail"] == (
        "Order not found."
    )


# ==========================================
# Admin Can Update Order Status
# ==========================================


def test_admin_can_update_order_status(
    client: TestClient,
    db: Session,
):
    admin = create_test_user(
        db,
        "admin-update-status@example.com",
        role="admin",
    )

    customer = create_test_user(
        db,
        "update-status-customer@example.com",
    )

    order = create_test_order(
        db,
        customer.id,
        status="paid",
    )

    response = client.patch(
        f"/admin/orders/{order.id}",
        headers=auth_headers(admin),
        json={
            "status": "processing",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == order.id
    assert data["user_id"] == customer.id
    assert data["status"] == "processing"

    db.refresh(order)

    assert order.status == "processing"


# ==========================================
# Admin Can Progress Through Statuses
# ==========================================


def test_admin_can_update_order_to_shipped(
    client: TestClient,
    db: Session,
):
    admin = create_test_user(
        db,
        "admin-shipped@example.com",
        role="admin",
    )

    customer = create_test_user(
        db,
        "shipped-customer@example.com",
    )

    order = create_test_order(
        db,
        customer.id,
        status="processing",
    )

    response = client.patch(
        f"/admin/orders/{order.id}",
        headers=auth_headers(admin),
        json={
            "status": "shipped",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "shipped"


# ==========================================
# Customer Cannot Update Order Status
# ==========================================


def test_customer_cannot_update_order_status(
    client: TestClient,
    db: Session,
):
    customer = create_test_user(
        db,
        "customer-update-status@example.com",
    )

    order = create_test_order(
        db,
        customer.id,
        status="pending",
    )

    response = client.patch(
        f"/admin/orders/{order.id}",
        headers=auth_headers(customer),
        json={
            "status": "shipped",
        },
    )

    assert response.status_code == 403

    assert response.json()["detail"] == (
        "Administrator access required."
    )


# ==========================================
# Unauthenticated Cannot Update Status
# ==========================================


def test_unauthenticated_cannot_update_order_status(
    client: TestClient,
    db: Session,
):
    customer = create_test_user(
        db,
        "unauthenticated-update-customer@example.com",
    )

    order = create_test_order(
        db,
        customer.id,
    )

    response = client.patch(
        f"/admin/orders/{order.id}",
        json={
            "status": "processing",
        },
    )

    assert response.status_code == 401


# ==========================================
# Invalid Status
# ==========================================


def test_admin_cannot_set_invalid_order_status(
    client: TestClient,
    db: Session,
):
    admin = create_test_user(
        db,
        "admin-invalid-status@example.com",
        role="admin",
    )

    customer = create_test_user(
        db,
        "invalid-status-customer@example.com",
    )

    order = create_test_order(
        db,
        customer.id,
        status="pending",
    )

    response = client.patch(
        f"/admin/orders/{order.id}",
        headers=auth_headers(admin),
        json={
            "status": "not-a-real-status",
        },
    )

    assert response.status_code == 400

    assert "Invalid order status" in (
        response.json()["detail"]
    )

    db.refresh(order)

    assert order.status == "pending"


# ==========================================
# Nonexistent Order Status Update
# ==========================================


def test_admin_cannot_update_nonexistent_order(
    client: TestClient,
    db: Session,
):
    admin = create_test_user(
        db,
        "admin-update-nonexistent@example.com",
        role="admin",
    )

    response = client.patch(
        "/admin/orders/999999",
        headers=auth_headers(admin),
        json={
            "status": "processing",
        },
    )

    assert response.status_code == 404

    assert response.json()["detail"] == (
        "Order not found."
    )


# ==========================================
# Status Update Does Not Change Total
# ==========================================


def test_status_update_preserves_order_total(
    client: TestClient,
    db: Session,
):
    admin = create_test_user(
        db,
        "admin-preserve-total@example.com",
        role="admin",
    )

    customer = create_test_user(
        db,
        "preserve-total-customer@example.com",
    )

    order = create_test_order(
        db,
        customer.id,
        status="shipped",
        total_amount=Decimal("249.99"),
    )

    response = client.patch(
        f"/admin/orders/{order.id}",
        headers=auth_headers(admin),
        json={
            "status": "delivered",
        },
    )

    assert response.status_code == 200

    db.refresh(order)

    assert order.status == "delivered"
    assert order.total_amount == Decimal("249.99")


# ==========================================
# Payment Statuses Are Not Admin Settable
# ==========================================


def test_admin_cannot_mark_order_paid(
    client: TestClient,
    db: Session,
):
    """
    Marking an order paid must require money to have moved.
    The API has to refuse it even for an administrator.
    """

    admin = create_test_user(
        db,
        "admin-cannot-mark-paid@example.com",
        role="admin",
    )

    customer = create_test_user(
        db,
        "cannot-mark-paid-customer@example.com",
    )

    order = create_test_order(
        db,
        customer.id,
        status="pending",
    )

    response = client.patch(
        f"/admin/orders/{order.id}",
        headers=auth_headers(admin),
        json={
            "status": "paid",
        },
    )

    assert response.status_code == 400

    assert "payment process" in (
        response.json()["detail"]
    )

    db.refresh(order)

    assert order.status == "pending"


# ==========================================
# Illegal Transitions Are Refused
# ==========================================


def test_admin_cannot_reverse_a_delivered_order(
    client: TestClient,
    db: Session,
):
    admin = create_test_user(
        db,
        "admin-cannot-reverse@example.com",
        role="admin",
    )

    customer = create_test_user(
        db,
        "cannot-reverse-customer@example.com",
    )

    order = create_test_order(
        db,
        customer.id,
        status="delivered",
    )

    response = client.patch(
        f"/admin/orders/{order.id}",
        headers=auth_headers(admin),
        json={
            "status": "processing",
        },
    )

    assert response.status_code == 400

    assert "cannot move from" in (
        response.json()["detail"]
    )

    db.refresh(order)

    assert order.status == "delivered"