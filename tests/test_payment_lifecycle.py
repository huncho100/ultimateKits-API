"""
Payment and order lifecycle integrity.

These exercise the services directly rather than through the
routes. The behaviour under test is what happens to the
payment row, the order and the cart when a provider result
arrives - not authentication or serialisation, which the
route tests already cover.
"""

import uuid
from decimal import Decimal

import httpx
import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.models.order import Order
from app.models.payment import Payment
from app.models.product import Product
from app.models.user import User
from app.services.payment_service import PaymentService


# ==========================================
# Test Helpers
# ==========================================

def create_test_user(db: Session) -> User:
    user = User(
        first_name="Lifecycle",
        last_name="Customer",
        email=(
            f"lifecycle_{uuid.uuid4().hex[:10]}"
            "@example.com"
        ),
        password_hash="test-password-hash",
        role="customer",
        is_active=True,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def create_test_product(
    db: Session,
    *,
    price: Decimal = Decimal("100.00"),
) -> Product:
    product = Product(
        name=f"Lifecycle Jersey {uuid.uuid4().hex[:6]}",
        sport="Football",
        category="Jerseys",
        team="Test Team",
        league="Test League",
        brand="Test Brand",
        price=price,
        old_price=None,
        rating=Decimal("4.50"),
        image=None,
        is_featured=False,
        is_new=False,
        is_best_seller=False,
        in_stock=True,
    )

    db.add(product)
    db.commit()
    db.refresh(product)

    return product


def create_test_order(
    db: Session,
    user: User,
    *,
    status: str = "pending",
    total_amount: Decimal = Decimal("100.00"),
) -> Order:
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
    db: Session,
    user: User,
    order: Order,
    *,
    status: str = "pending",
) -> Payment:
    payment = Payment(
        order_id=order.id,
        user_id=user.id,
        provider="paystack",
        reference=f"UK-LIFE-{uuid.uuid4().hex}",
        amount=order.total_amount,
        currency="NGN",
        status=status,
    )

    db.add(payment)
    db.commit()
    db.refresh(payment)

    return payment


def stock_cart(
    db: Session,
    user: User,
    *,
    quantity: int = 2,
) -> Cart:
    """
    Give a user a cart with one product in it.
    """

    product = create_test_product(db)

    cart = Cart(user_id=user.id)

    db.add(cart)
    db.commit()
    db.refresh(cart)

    db.add(
        CartItem(
            cart_id=cart.id,
            product_id=product.id,
            quantity=quantity,
        )
    )

    db.commit()
    db.refresh(cart)

    return cart


def provider_result(
    payment: Payment,
    *,
    status: str = "success",
) -> dict:
    return {
        "reference": payment.reference,
        "amount": int(payment.amount * 100),
        "currency": "NGN",
        "status": status,
        "channel": "card",
        "id": 777_001,
    }


class MockResponse:
    def __init__(self, json_data, status_code=200):
        self.status_code = status_code
        self._json_data = json_data

    def json(self):
        return self._json_data


def mock_initialize_ok(*args, **kwargs):
    return MockResponse(
        {
            "status": True,
            "data": {
                "authorization_url": (
                    "https://checkout.paystack.com/ok"
                ),
                "access_code": "access-code",
                "reference": kwargs["json"]["reference"],
            },
        }
    )


# ==========================================
# Initialization Failure Does Not Leak Rows
# ==========================================

def test_initialization_failure_marks_payment_failed(
    db: Session,
    monkeypatch,
):
    """
    A payment row is written before the provider is called,
    so a provider failure used to leave a row pending
    forever with nothing able to settle it.
    """

    user = create_test_user(db)

    order = create_test_order(db, user)

    def mock_post(*args, **kwargs):
        raise httpx.RequestError("connection refused")

    monkeypatch.setattr(httpx, "post", mock_post)

    with pytest.raises(HTTPException) as error:
        PaymentService.initialize_payment(db, order, user)

    assert error.value.status_code == 502

    payment = (
        db.query(Payment)
        .filter(Payment.order_id == order.id)
        .one()
    )

    assert payment.status == "failed"

    db.refresh(order)

    # The order itself is untouched, so the customer can
    # simply try again.
    assert order.status == "pending"


def test_order_is_payable_after_a_failed_initialization(
    db: Session,
    monkeypatch,
):
    user = create_test_user(db)

    order = create_test_order(db, user)

    def mock_post(*args, **kwargs):
        raise httpx.RequestError("connection refused")

    monkeypatch.setattr(httpx, "post", mock_post)

    with pytest.raises(HTTPException):
        PaymentService.initialize_payment(db, order, user)

    monkeypatch.setattr(httpx, "post", mock_initialize_ok)

    result = PaymentService.initialize_payment(
        db,
        order,
        user,
    )

    assert result.reference.startswith("UK-")


# ==========================================
# Repeated Initialization
# ==========================================

def test_reinitialization_supersedes_previous_attempt(
    db: Session,
    monkeypatch,
):
    """
    Clicking "pay" twice used to leave two live references,
    both pending, with no way to tell which one the customer
    would actually use.
    """

    user = create_test_user(db)

    order = create_test_order(db, user)

    monkeypatch.setattr(httpx, "post", mock_initialize_ok)

    first = PaymentService.initialize_payment(
        db,
        order,
        user,
    )

    second = PaymentService.initialize_payment(
        db,
        order,
        user,
    )

    assert first.reference != second.reference

    payments = (
        db.query(Payment)
        .filter(Payment.order_id == order.id)
        .all()
    )

    assert len(payments) == 2

    by_reference = {
        payment.reference: payment.status
        for payment in payments
    }

    assert by_reference[first.reference] == "abandoned"
    assert by_reference[second.reference] == "pending"


def test_settlement_abandons_the_other_attempt(
    db: Session,
    monkeypatch,
):
    """
    The superseded reference is still live at Paystack. If
    the customer pays the newer one, the older must stop
    looking like an outstanding payment.
    """

    user = create_test_user(db)

    order = create_test_order(db, user)

    monkeypatch.setattr(httpx, "post", mock_initialize_ok)

    first = PaymentService.initialize_payment(
        db,
        order,
        user,
    )

    PaymentService.initialize_payment(db, order, user)

    # Bring the first attempt back to pending, as though the
    # customer had returned to that Paystack page instead.
    stale = PaymentService.get_payment_by_reference(
        db,
        first.reference,
    )

    stale.status = "pending"

    db.commit()

    newest = (
        db.query(Payment)
        .filter(
            Payment.order_id == order.id,
            Payment.reference != first.reference,
        )
        .one()
    )

    PaymentService.settle_payment(
        db,
        newest,
        provider_result(newest),
    )

    db.refresh(stale)

    assert stale.status == "abandoned"

    # The order's payment is the one that actually succeeded,
    # not merely the most recent row.
    assert (
        PaymentService.get_order_payment(db, order.id).id
        == newest.id
    )


# ==========================================
# Unpayable Orders
# ==========================================

def test_cannot_initialize_payment_for_cancelled_order(
    db: Session,
):
    """
    Taking money for a cancelled order charges a customer
    for something that will never be sent.
    """

    user = create_test_user(db)

    order = create_test_order(
        db,
        user,
        status="cancelled",
    )

    with pytest.raises(HTTPException) as error:
        PaymentService.initialize_payment(db, order, user)

    assert error.value.status_code == 400

    assert "can no longer be paid for" in (
        error.value.detail
    )


def test_cannot_initialize_payment_for_shipped_order(
    db: Session,
):
    user = create_test_user(db)

    order = create_test_order(
        db,
        user,
        status="shipped",
    )

    with pytest.raises(HTTPException) as error:
        PaymentService.initialize_payment(db, order, user)

    assert error.value.status_code == 400


# ==========================================
# Cart Is Emptied On Payment, Not On Order
# ==========================================

def test_successful_settlement_clears_the_cart(
    db: Session,
):
    user = create_test_user(db)

    cart = stock_cart(db, user)

    order = create_test_order(db, user)

    payment = create_test_payment(db, user, order)

    PaymentService.settle_payment(
        db,
        payment,
        provider_result(payment),
    )

    db.refresh(cart)

    assert cart.items == []
    assert payment.order.status == "paid"


def test_failed_settlement_keeps_the_cart(
    db: Session,
):
    """
    A declined card must not cost the customer their basket.
    """

    user = create_test_user(db)

    cart = stock_cart(db, user)

    order = create_test_order(db, user)

    payment = create_test_payment(db, user, order)

    PaymentService.settle_payment(
        db,
        payment,
        provider_result(payment, status="failed"),
    )

    db.refresh(cart)

    assert len(cart.items) == 1
    assert payment.order.status == "payment_failed"


def test_replayed_success_does_not_wipe_a_new_cart(
    db: Session,
):
    """
    The customer paid, then started shopping again. A
    duplicate event for the old order must leave the new
    basket alone.
    """

    user = create_test_user(db)

    order = create_test_order(db, user)

    payment = create_test_payment(db, user, order)

    PaymentService.settle_payment(
        db,
        payment,
        provider_result(payment),
    )

    cart = stock_cart(db, user, quantity=3)

    PaymentService.settle_payment(
        db,
        payment,
        provider_result(payment),
    )

    db.refresh(cart)

    assert len(cart.items) == 1
    assert cart.items[0].quantity == 3


# ==========================================
# Settlement Respects The Order State Machine
# ==========================================

def test_settlement_does_not_reverse_fulfilment(
    db: Session,
):
    """
    A webhook that arrives after an operator has already
    shipped the goods must not drag the order back to
    "paid", which would make it eligible for processing all
    over again.
    """

    user = create_test_user(db)

    order = create_test_order(
        db,
        user,
        status="shipped",
    )

    payment = create_test_payment(db, user, order)

    PaymentService.settle_payment(
        db,
        payment,
        provider_result(payment),
    )

    db.refresh(order)

    # The money is recorded, the fulfilment state is not
    # disturbed.
    assert payment.status == "success"
    assert order.status == "shipped"


def test_settlement_does_not_revive_a_cancelled_order(
    db: Session,
):
    user = create_test_user(db)

    order = create_test_order(
        db,
        user,
        status="cancelled",
    )

    payment = create_test_payment(db, user, order)

    PaymentService.settle_payment(
        db,
        payment,
        provider_result(payment),
    )

    db.refresh(order)

    assert payment.status == "success"
    assert order.status == "cancelled"


def test_failure_after_payment_does_not_unpay_an_order(
    db: Session,
):
    """
    A late failure event for a payment that already
    succeeded is ignored outright.
    """

    user = create_test_user(db)

    order = create_test_order(db, user)

    payment = create_test_payment(db, user, order)

    PaymentService.settle_payment(
        db,
        payment,
        provider_result(payment),
    )

    PaymentService.settle_payment(
        db,
        payment,
        provider_result(payment, status="failed"),
    )

    db.refresh(order)

    assert payment.status == "success"
    assert order.status == "paid"


def test_unrecognised_provider_status_leaves_order_alone(
    db: Session,
):
    """
    Paystack reporting something this system does not model
    must not be guessed at.
    """

    user = create_test_user(db)

    order = create_test_order(db, user)

    payment = create_test_payment(db, user, order)

    PaymentService.settle_payment(
        db,
        payment,
        provider_result(payment, status="reversed"),
    )

    db.refresh(order)

    assert payment.status == "reversed"
    assert order.status == "pending"
