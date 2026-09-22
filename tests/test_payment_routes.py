from decimal import Decimal
import uuid

import httpx

from app.models.order import Order
from app.models.payment import Payment
from app.models.user import User
from app.utils.security import create_access_token


# ==========================================
# Test Helpers
# ==========================================

def create_test_user(
    db,
    *,
    role: str = "customer",
) -> User:
    """
    Create a user for payment route tests.
    """

    user = User(
        first_name="Payment",
        last_name="Route Test",
        email=(
            f"payment_route_{uuid.uuid4().hex[:10]}"
            "@example.com"
        ),
        password_hash="test-password-hash",
        role=role,
        is_active=True,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def auth_headers(
    user: User,
) -> dict:
    """
    Generate authentication headers for
    a test user.
    """

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


def create_test_order(
    db,
    user: User,
    *,
    status: str = "pending",
    total_amount: Decimal = Decimal("100.00"),
) -> Order:
    """
    Create an order for payment route tests.
    """

    order = Order(
        user_id=user.id,
        status=status,
        total_amount=total_amount,
    )

    db.add(order)
    db.commit()
    db.refresh(order)

    return order


def create_test_payment(
    db,
    user: User,
    order: Order,
    *,
    reference: str | None = None,
    amount: Decimal | None = None,
    status: str = "pending",
) -> Payment:
    """
    Create a payment for verification tests.
    """

    payment = Payment(
        order_id=order.id,
        user_id=user.id,
        provider="paystack",
        reference=(
            reference
            or f"UK-TEST-{uuid.uuid4().hex}"
        ),
        amount=(
            amount
            if amount is not None
            else order.total_amount
        ),
        currency="NGN",
        status=status,
    )

    db.add(payment)
    db.commit()
    db.refresh(payment)

    return payment


# ==========================================
# Mock Response
# ==========================================

class MockResponse:
    """
    Mock HTTP response for Paystack requests.
    """

    def __init__(
        self,
        *,
        status_code: int = 200,
        json_data=None,
    ):
        self.status_code = status_code
        self._json_data = json_data

    def json(self):
        return self._json_data


# ==========================================
# Initialize Payment Success
# ==========================================

def test_initialize_payment_success(
    client,
    db,
    monkeypatch,
):
    """
    Authenticated users can initialize payment
    for their own order.
    """

    user = create_test_user(db)

    order = create_test_order(
        db,
        user,
        total_amount=Decimal("150.00"),
    )

    def mock_post(
        *args,
        **kwargs,
    ):
        return MockResponse(
            status_code=200,
            json_data={
                "status": True,
                "data": {
                    "authorization_url": (
                        "https://checkout.paystack.com/"
                        "test"
                    ),
                    "access_code": "test-access-code",
                    "reference": "test-reference",
                },
            },
        )

    monkeypatch.setattr(
        httpx,
        "post",
        mock_post,
    )

    response = client.post(
        f"/payments/initialize/{order.id}",
        headers=auth_headers(user),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["authorization_url"] == (
        "https://checkout.paystack.com/test"
    )

    assert data["access_code"] == (
        "test-access-code"
    )

    assert data["reference"] == (
        "test-reference"
    )

    payment = (
        db.query(Payment)
        .filter(
            Payment.order_id == order.id,
        )
        .first()
    )

    assert payment is not None
    assert payment.user_id == user.id
    assert payment.amount == Decimal("150.00")
    assert payment.status == "pending"
    assert payment.currency == "NGN"

    print(
        "✓ Initialize payment success "
        "route test passed"
    )


# ==========================================
# Initialize Payment Order Not Found
# ==========================================

def test_initialize_payment_order_not_found(
    client,
    db,
):
    """
    Initializing payment for a nonexistent
    order should return 404.
    """

    user = create_test_user(db)

    response = client.post(
        "/payments/initialize/999999",
        headers=auth_headers(user),
    )

    assert response.status_code == 404

    data = response.json()

    assert data["detail"] == (
        "Order not found."
    )

    print(
        "✓ Initialize payment nonexistent "
        "order test passed"
    )


# ==========================================
# Initialize Another User's Order
# ==========================================

def test_initialize_payment_other_user_order(
    client,
    db,
):
    """
    Users cannot initialize payment for
    another user's order.
    """

    owner = create_test_user(db)

    other_user = create_test_user(db)

    order = create_test_order(
        db,
        owner,
    )

    response = client.post(
        f"/payments/initialize/{order.id}",
        headers=auth_headers(other_user),
    )

    assert response.status_code == 403

    data = response.json()

    assert data["detail"] == (
        "You do not have access to this order."
    )

    print(
        "✓ Initialize payment ownership "
        "test passed"
    )


# ==========================================
# Initialize Requires Authentication
# ==========================================

def test_initialize_payment_requires_authentication(
    client,
    db,
):
    """
    Payment initialization requires
    authentication.
    """

    user = create_test_user(db)

    order = create_test_order(
        db,
        user,
    )

    response = client.post(
        f"/payments/initialize/{order.id}",
    )

    assert response.status_code == 401

    print(
        "✓ Initialize payment authentication "
        "test passed"
    )


# ==========================================
# Initialize Paid Order
# ==========================================

def test_initialize_payment_paid_order(
    client,
    db,
):
    """
    Payment cannot be initialized for an
    already paid order.
    """

    user = create_test_user(db)

    order = create_test_order(
        db,
        user,
        status="paid",
    )

    response = client.post(
        f"/payments/initialize/{order.id}",
        headers=auth_headers(user),
    )

    assert response.status_code == 400

    data = response.json()

    assert data["detail"] == (
        "This order has already been paid for."
    )

    print(
        "✓ Initialize paid order test passed"
    )


# ==========================================
# Initialize Zero Amount
# ==========================================

def test_initialize_payment_zero_amount(
    client,
    db,
):
    """
    Payment cannot be initialized for an
    order with zero amount.
    """

    user = create_test_user(db)

    order = create_test_order(
        db,
        user,
        total_amount=Decimal("0.00"),
    )

    response = client.post(
        f"/payments/initialize/{order.id}",
        headers=auth_headers(user),
    )

    assert response.status_code == 400

    data = response.json()

    assert data["detail"] == (
        "Order total must be greater than zero."
    )

    print(
        "✓ Initialize zero amount test passed"
    )


# ==========================================
# Verify Payment Success
# ==========================================

def test_verify_payment_success(
    client,
    db,
    monkeypatch,
):
    """
    Authenticated users can verify their
    successful payment.
    """

    user = create_test_user(db)

    order = create_test_order(
        db,
        user,
        total_amount=Decimal("100.00"),
    )

    payment = create_test_payment(
        db,
        user,
        order,
        reference="UK-VERIFY-SUCCESS",
    )

    def mock_get(
        *args,
        **kwargs,
    ):
        return MockResponse(
            status_code=200,
            json_data={
                "status": True,
                "data": {
                    "amount": 10000,
                    "currency": "NGN",
                    "status": "success",
                    "channel": "card",
                    "id": 123456,
                    "paid_at": (
                        "2026-09-07T12:00:00Z"
                    ),
                },
            },
        )

    monkeypatch.setattr(
        httpx,
        "get",
        mock_get,
    )

    response = client.get(
        f"/payments/verify/{payment.reference}",
        headers=auth_headers(user),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["reference"] == (
        payment.reference
    )

    assert data["status"] == "success"

    assert Decimal(
        data["amount"]
    ) == Decimal("100.00")

    assert data["currency"] == "NGN"

    assert data["channel"] == "card"

    db.refresh(payment)
    db.refresh(order)

    assert payment.status == "success"

    assert payment.channel == "card"

    assert payment.provider_transaction_id == (
        "123456"
    )

    assert order.status == "paid"

    print(
        "✓ Verify payment success route "
        "test passed"
    )


# ==========================================
# Verify Payment Not Found
# ==========================================

def test_verify_payment_not_found(
    client,
    db,
):
    """
    Verifying a nonexistent payment should
    return 404.
    """

    user = create_test_user(db)

    response = client.get(
        "/payments/verify/UK-NOT-FOUND",
        headers=auth_headers(user),
    )

    assert response.status_code == 404

    data = response.json()

    assert data["detail"] == (
        "Payment not found."
    )

    print(
        "✓ Verify payment not found "
        "test passed"
    )


# ==========================================
# Verify Another User's Payment
# ==========================================

def test_verify_payment_other_user(
    client,
    db,
):
    """
    Users cannot verify another user's
    payment.
    """

    owner = create_test_user(db)

    other_user = create_test_user(db)

    order = create_test_order(
        db,
        owner,
    )

    payment = create_test_payment(
        db,
        owner,
        order,
    )

    response = client.get(
        f"/payments/verify/{payment.reference}",
        headers=auth_headers(other_user),
    )

    assert response.status_code == 403

    data = response.json()

    assert data["detail"] == (
        "You do not have access to this payment."
    )

    print(
        "✓ Verify payment ownership "
        "test passed"
    )


# ==========================================
# Verify Requires Authentication
# ==========================================

def test_verify_payment_requires_authentication(
    client,
    db,
):
    """
    Payment verification requires
    authentication.
    """

    user = create_test_user(db)

    order = create_test_order(
        db,
        user,
    )

    payment = create_test_payment(
        db,
        user,
        order,
    )

    response = client.get(
        f"/payments/verify/{payment.reference}",
    )

    assert response.status_code == 401

    print(
        "✓ Verify payment authentication "
        "test passed"
    )


# ==========================================
# Verify Payment Amount Mismatch
# ==========================================

def test_verify_payment_amount_mismatch(
    client,
    db,
    monkeypatch,
):
    """
    Verification should fail when Paystack's
    amount does not match the local payment.
    """

    user = create_test_user(db)

    order = create_test_order(
        db,
        user,
        total_amount=Decimal("100.00"),
    )

    payment = create_test_payment(
        db,
        user,
        order,
        amount=Decimal("100.00"),
    )

    def mock_get(
        *args,
        **kwargs,
    ):
        return MockResponse(
            status_code=200,
            json_data={
                "status": True,
                "data": {
                    "amount": 5000,
                    "currency": "NGN",
                    "status": "success",
                    "channel": "card",
                    "id": 123456,
                },
            },
        )

    monkeypatch.setattr(
        httpx,
        "get",
        mock_get,
    )

    response = client.get(
        f"/payments/verify/{payment.reference}",
        headers=auth_headers(user),
    )

    assert response.status_code == 400

    data = response.json()

    assert data["detail"] == (
        "Payment amount does not match "
        "the order amount."
    )

    db.refresh(payment)
    db.refresh(order)

    assert payment.status == "pending"

    assert order.status == "pending"

    print(
        "✓ Verify payment amount mismatch "
        "test passed"
    )


# ==========================================
# Verify Failed Payment
# ==========================================

def test_verify_payment_failed(
    client,
    db,
    monkeypatch,
):
    """
    Failed payment verification should update
    the payment and order status.
    """

    user = create_test_user(db)

    order = create_test_order(
        db,
        user,
        total_amount=Decimal("100.00"),
    )

    payment = create_test_payment(
        db,
        user,
        order,
        reference="UK-VERIFY-FAILED",
    )

    def mock_get(
        *args,
        **kwargs,
    ):
        return MockResponse(
            status_code=200,
            json_data={
                "status": True,
                "data": {
                    "amount": 10000,
                    "currency": "NGN",
                    "status": "failed",
                    "channel": "card",
                    "id": 987654,
                },
            },
        )

    monkeypatch.setattr(
        httpx,
        "get",
        mock_get,
    )

    response = client.get(
        f"/payments/verify/{payment.reference}",
        headers=auth_headers(user),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "failed"

    db.refresh(payment)
    db.refresh(order)

    assert payment.status == "failed"

    assert order.status == "payment_failed"

    assert payment.provider_transaction_id == (
        "987654"
    )

    print(
        "✓ Verify failed payment test passed"
    )