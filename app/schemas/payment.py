from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


# ==========================================
# Payment Initialize Response
# ==========================================

class PaymentInitializeResponse(BaseModel):
    """
    Response returned after initializing a
    Paystack payment transaction.
    """

    authorization_url: str
    access_code: str
    reference: str


# ==========================================
# Payment Response
# ==========================================

class PaymentResponse(BaseModel):
    """
    Schema returned by the API when exposing
    payment information.
    """

    id: int
    order_id: int
    user_id: int

    provider: str
    reference: str

    amount: Decimal
    currency: str

    status: str
    channel: str | None

    provider_transaction_id: str | None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )


# ==========================================
# Payment Verification Response
# ==========================================

class PaymentVerificationResponse(BaseModel):
    """
    Response returned after verifying a payment
    with the payment provider.
    """

    reference: str
    status: str
    amount: Decimal
    currency: str
    channel: str | None
    paid_at: datetime | None


# ==========================================
# Payment Webhook Response
# ==========================================

class PaymentWebhookResponse(BaseModel):
    """
    Acknowledgement returned to the payment provider.

    Paystack retries any event it does not see acknowledged,
    so this is returned for events that were applied and for
    events that were deliberately ignored alike. "outcome"
    records which, for operators reading provider logs.
    """

    status: str
    outcome: str