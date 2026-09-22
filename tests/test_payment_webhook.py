import hashlib
import hmac
import json
import uuid
from decimal import Decimal

from app.core.config import settings
from app.models.order import Order
from app.models.payment import Payment
from app.models.user import User


# ==========================================
# Test Helpers
# ==========================================

def create_test_user(db) -> User:
    user = User(
        first_name="Webhook",
        last_name="Customer",
        email=(
            f"webhook_{uuid.uuid4().hex[:8]}"
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


def create_test_payment(
    db,
    *,
    amount: Decimal = Decimal("100.00"),
    currency: str = "NGN",
    payment_status: str = "pending",
    order_status: str = "pending",
) -> Payment:
    user = create_test_user(db)

    order = Order(
        user_id=user.id,
        status=order_status,
        total_amount=amount,
    )

    db.add(order)
    db.commit()
    db.refresh(order)

    payment = Payment(
        order_id=order.id,
        user_id=user.id,
        provider="paystack",
        reference=f"UK-HOOK-{uuid.uuid4().hex}",
        amount=amount,
        currency=currency,
        status=payment_status,
    )

    db.add(payment)
    db.commit()
    db.refresh(payment)

    return payment


def signed_post(client, event: dict):
    """
    Post an event signed the way Paystack signs it: HMAC
    SHA-512 over the exact request body, keyed on the secret.
    """

    body = json.dumps(event).encode("utf-8")

    signature = hmac.new(
        settings.PAYSTACK_SECRET_KEY.encode("utf-8"),
        body,
        hashlib.sha512,
    ).hexdigest()

    return client.post(
        "/payments/webhook",
        content=body,
        headers={
            "Content-Type": "application/json",
            "x-paystack-signature": signature,
        },
    )


def charge_success(
    payment: Payment,
    *,
    amount_in_kobo: int | None = None,
    currency: str = "NGN",
) -> dict:
    return {
        "event": "charge.success",
        "data": {
            "reference": payment.reference,
            "amount": (
                amount_in_kobo
                if amount_in_kobo is not None
                else int(payment.amount * 100)
            ),
            "currency": currency,
            "status": "success",
            "channel": "card",
            "id": 424242,
        },
    }


# ==========================================
# Signature Verification
# ==========================================

def test_webhook_rejects_missing_signature(client, db):
    payment = create_test_payment(db)

    response = client.post(
        "/payments/webhook",
        json=charge_success(payment),
    )

    assert response.status_code == 401

    db.refresh(payment)

    assert payment.status == "pending"


def test_webhook_rejects_forged_signature(client, db):
    payment = create_test_payment(db)

    response = client.post(
        "/payments/webhook",
        json=charge_success(payment),
        headers={
            "x-paystack-signature": "a" * 128,
        },
    )

    assert response.status_code == 401

    db.refresh(payment)

    assert payment.status == "pending"
    assert payment.order.status == "pending"


def test_webhook_rejects_tampered_body(client, db):
    """
    A signature valid for one payload must not authenticate
    a different one.
    """

    payment = create_test_payment(db)

    event = charge_success(payment)

    body = json.dumps(event).encode("utf-8")

    signature = hmac.new(
        settings.PAYSTACK_SECRET_KEY.encode("utf-8"),
        body,
        hashlib.sha512,
    ).hexdigest()

    tampered = json.dumps(
        charge_success(
            payment,
            amount_in_kobo=1,
        )
    ).encode("utf-8")

    response = client.post(
        "/payments/webhook",
        content=tampered,
        headers={
            "Content-Type": "application/json",
            "x-paystack-signature": signature,
        },
    )

    assert response.status_code == 401


def test_webhook_requires_no_authentication(client, db):
    """
    Paystack cannot hold a user session, so the endpoint
    must succeed with no Authorization header at all.
    """

    payment = create_test_payment(db)

    response = signed_post(
        client,
        charge_success(payment),
    )

    assert response.status_code == 200


# ==========================================
# Settlement
# ==========================================

def test_webhook_settles_successful_charge(client, db):
    """
    The whole point: an order is paid even though the
    customer never returned to the callback page.
    """

    payment = create_test_payment(db)

    response = signed_post(
        client,
        charge_success(payment),
    )

    assert response.status_code == 200
    assert response.json()["outcome"] == "settled"

    db.refresh(payment)

    assert payment.status == "success"
    assert payment.channel == "card"
    assert payment.provider_transaction_id == "424242"
    assert payment.order.status == "paid"


def test_webhook_is_idempotent(client, db):
    """
    Paystack retries until acknowledged, so the same event
    arriving twice must settle once.
    """

    payment = create_test_payment(db)

    first = signed_post(
        client,
        charge_success(payment),
    )

    second = signed_post(
        client,
        charge_success(payment),
    )

    assert first.json()["outcome"] == "settled"
    assert second.status_code == 200
    assert second.json()["outcome"] == "already_settled"

    db.refresh(payment)

    assert payment.status == "success"
    assert payment.order.status == "paid"


def test_webhook_rejects_amount_mismatch(client, db):
    """
    A correctly signed event for the wrong amount must never
    mark the order paid.
    """

    payment = create_test_payment(
        db,
        amount=Decimal("100.00"),
    )

    response = signed_post(
        client,
        charge_success(
            payment,
            amount_in_kobo=1_00,
        ),
    )

    assert response.status_code == 200
    assert response.json()["outcome"] == "mismatch"

    db.refresh(payment)

    assert payment.status == "pending"
    assert payment.order.status == "pending"


def test_webhook_rejects_currency_mismatch(client, db):
    """
    100 of a stronger unit is not 100 naira. The currency
    has to be checked independently of the number.
    """

    payment = create_test_payment(
        db,
        amount=Decimal("100.00"),
    )

    response = signed_post(
        client,
        charge_success(
            payment,
            currency="USD",
        ),
    )

    assert response.status_code == 200
    assert response.json()["outcome"] == "mismatch"

    db.refresh(payment)

    assert payment.status == "pending"
    assert payment.order.status == "pending"


def test_webhook_rejects_missing_currency(client, db):
    """
    An absent currency cannot be assumed to be ours.
    """

    payment = create_test_payment(db)

    event = charge_success(payment)

    del event["data"]["currency"]

    response = signed_post(client, event)

    assert response.status_code == 200
    assert response.json()["outcome"] == "mismatch"

    db.refresh(payment)

    assert payment.status == "pending"


# ==========================================
# Events We Do Not Act On
# ==========================================

def test_webhook_acknowledges_unrelated_event(client, db):
    payment = create_test_payment(db)

    response = signed_post(
        client,
        {
            "event": "transfer.success",
            "data": {
                "reference": payment.reference,
                "amount": 10000,
                "currency": "NGN",
                "status": "success",
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["outcome"] == "ignored"

    db.refresh(payment)

    assert payment.status == "pending"


def test_webhook_acknowledges_unknown_reference(client, db):
    response = signed_post(
        client,
        {
            "event": "charge.success",
            "data": {
                "reference": "UK-DOES-NOT-EXIST",
                "amount": 10000,
                "currency": "NGN",
                "status": "success",
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["outcome"] == "unknown"


def test_webhook_rejects_malformed_payload(client):
    body = b"{not json"

    signature = hmac.new(
        settings.PAYSTACK_SECRET_KEY.encode("utf-8"),
        body,
        hashlib.sha512,
    ).hexdigest()

    response = client.post(
        "/payments/webhook",
        content=body,
        headers={
            "Content-Type": "application/json",
            "x-paystack-signature": signature,
        },
    )

    assert response.status_code == 400


# ==========================================
# Shared Settlement Path
# ==========================================

def test_webhook_does_not_downgrade_a_paid_order(
    client,
    db,
):
    """
    A stale or replayed failure event arriving after a
    success must not move an order back out of "paid".
    """

    payment = create_test_payment(db)

    signed_post(
        client,
        charge_success(payment),
    )

    db.refresh(payment)

    assert payment.status == "success"

    failed_event = charge_success(payment)
    failed_event["data"]["status"] = "failed"

    response = signed_post(client, failed_event)

    assert response.status_code == 200

    db.refresh(payment)

    assert payment.status == "success"
    assert payment.order.status == "paid"
