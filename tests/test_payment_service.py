from datetime import datetime
from decimal import Decimal
from uuid import uuid4

import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.order import Order
from app.models.payment import Payment
from app.models.user import User
from app.schemas.payment import (
    PaymentInitializeResponse,
    PaymentVerificationResponse,
)


class PaymentService:
    """
    Handles Paystack payment initialization,
    verification, and local payment records.
    """

    # ==========================================
    # Initialize Payment
    # ==========================================

    @staticmethod
    def initialize_payment(
        db: Session,
        order: Order,
        user: User,
    ) -> PaymentInitializeResponse:
        """
        Initialize a Paystack payment transaction
        for an authenticated user's order.
        """

        # --------------------------------------
        # Validate Order Ownership
        # --------------------------------------

        if order.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this order.",
            )

        # --------------------------------------
        # Validate Order Amount
        # --------------------------------------

        if order.total_amount <= Decimal("0.00"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Order amount must be greater than zero.",
            )

        # --------------------------------------
        # Generate Payment Reference
        # --------------------------------------

        reference = f"UK-{uuid4().hex}"

        # --------------------------------------
        # Create Local Payment Record
        # --------------------------------------

        payment = Payment(
            order_id=order.id,
            user_id=user.id,
            provider="paystack",
            reference=reference,
            amount=order.total_amount,
            currency="NGN",
            status="pending",
        )

        db.add(payment)
        db.commit()
        db.refresh(payment)

        # --------------------------------------
        # Convert Amount To Kobo
        # --------------------------------------

        amount_in_kobo = int(
            order.total_amount * Decimal("100")
        )

        # --------------------------------------
        # Paystack Request
        # --------------------------------------

        headers = {
            "Authorization": (
                f"Bearer {settings.PAYSTACK_SECRET_KEY}"
            ),
            "Content-Type": "application/json",
        }

        payload = {
            "email": user.email,
            "amount": amount_in_kobo,
            "currency": "NGN",
            "reference": reference,
            "callback_url": (
                settings.PAYSTACK_CALLBACK_URL
            ),
        }

        try:
            with httpx.Client(
                timeout=30.0,
            ) as client:

                response = client.post(
                    (
                        f"{settings.PAYSTACK_BASE_URL}"
                        "/transaction/initialize"
                    ),
                    headers=headers,
                    json=payload,
                )

        except httpx.RequestError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "Unable to connect to the "
                    "payment provider."
                ),
            )

        # --------------------------------------
        # Handle Paystack Error
        # --------------------------------------

        if response.status_code >= 400:

            payment.status = "failed"

            db.commit()

            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=(
                    "Payment provider could not "
                    "initialize the transaction."
                ),
            )

        # --------------------------------------
        # Parse Response
        # --------------------------------------

        response_data = response.json()

        if not response_data.get("status"):

            payment.status = "failed"

            db.commit()

            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=(
                    "Payment initialization failed."
                ),
            )

        data = response_data.get("data")

        if not data:

            payment.status = "failed"

            db.commit()

            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=(
                    "Payment provider returned "
                    "an invalid response."
                ),
            )

        # --------------------------------------
        # Return Initialization Details
        # --------------------------------------

        return PaymentInitializeResponse(
            authorization_url=data[
                "authorization_url"
            ],
            access_code=data[
                "access_code"
            ],
            reference=data[
                "reference"
            ],
        )

    # ==========================================
    # Verify Payment
    # ==========================================

    @staticmethod
    def verify_payment(
        db: Session,
        reference: str,
        user: User,
    ) -> PaymentVerificationResponse:
        """
        Verify a Paystack payment transaction
        and update the local payment record.
        """

        # --------------------------------------
        # Get Local Payment
        # --------------------------------------

        payment = (
            db.query(Payment)
            .filter(
                Payment.reference == reference,
            )
            .first()
        )

        if payment is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found.",
            )

        # --------------------------------------
        # Validate Payment Ownership
        # --------------------------------------

        if payment.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "You do not have access to "
                    "this payment."
                ),
            )

        # --------------------------------------
        # Paystack Request
        # --------------------------------------

        headers = {
            "Authorization": (
                f"Bearer {settings.PAYSTACK_SECRET_KEY}"
            ),
        }

        try:
            with httpx.Client(
                timeout=30.0,
            ) as client:

                response = client.get(
                    (
                        f"{settings.PAYSTACK_BASE_URL}"
                        "/transaction/verify/"
                        f"{reference}"
                    ),
                    headers=headers,
                )

        except httpx.RequestError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "Unable to connect to the "
                    "payment provider."
                ),
            )

        # --------------------------------------
        # Handle Paystack Error
        # --------------------------------------

        if response.status_code >= 400:

            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=(
                    "Payment provider could not "
                    "verify the transaction."
                ),
            )

        # --------------------------------------
        # Parse Response
        # --------------------------------------

        response_data = response.json()

        if not response_data.get("status"):

            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Payment verification failed.",
            )

        data = response_data.get("data")

        if not data:

            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=(
                    "Payment provider returned "
                    "an invalid response."
                ),
            )

        # --------------------------------------
        # Extract Payment Data
        # --------------------------------------

        provider_status = data.get("status")

        amount = (
            Decimal(str(data.get("amount", 0)))
            / Decimal("100")
        ).quantize(
            Decimal("0.01")
        )

        currency = data.get(
            "currency",
            "NGN",
        )

        channel = data.get("channel")

        provider_transaction_id = (
            str(data.get("id"))
            if data.get("id") is not None
            else None
        )

        paid_at = None

        paid_at_value = data.get("paid_at")

        if paid_at_value:

            try:
                paid_at = datetime.fromisoformat(
                    paid_at_value.replace(
                        "Z",
                        "+00:00",
                    )
                )
            except ValueError:
                paid_at = None

        # --------------------------------------
        # Validate Amount
        # --------------------------------------

        if amount != payment.amount:

            payment.status = "failed"

            db.commit()

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Payment amount does not match "
                    "the expected order amount."
                ),
            )

        # --------------------------------------
        # Update Local Payment
        # --------------------------------------

        payment.status = provider_status
        payment.currency = currency
        payment.channel = channel
        payment.provider_transaction_id = (
            provider_transaction_id
        )

        # --------------------------------------
        # Update Order On Success
        # --------------------------------------

        if provider_status == "success":

            payment.order.status = "paid"

        db.commit()
        db.refresh(payment)

        # --------------------------------------
        # Return Verification Result
        # --------------------------------------

        return PaymentVerificationResponse(
            reference=payment.reference,
            status=payment.status,
            amount=payment.amount,
            currency=payment.currency,
            channel=payment.channel,
            paid_at=paid_at,
        )