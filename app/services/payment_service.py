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
    Handles payment-related business logic and
    Paystack integration.
    """

    # ==========================================
    # Get Payment By Reference
    # ==========================================

    @staticmethod
    def get_payment_by_reference(
        db: Session,
        reference: str,
    ) -> Payment | None:
        """
        Retrieve a payment using its unique
        payment reference.
        """

        return (
            db.query(Payment)
            .filter(
                Payment.reference == reference,
            )
            .first()
        )

    # ==========================================
    # Get Order Payment
    # ==========================================

    @staticmethod
    def get_order_payment(
        db: Session,
        order_id: int,
    ) -> Payment | None:
        """
        Retrieve the most recent payment for
        an order.
        """

        return (
            db.query(Payment)
            .filter(
                Payment.order_id == order_id,
            )
            .order_by(
                Payment.created_at.desc(),
            )
            .first()
        )

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
        for an order.
        """

        # --------------------------------------
        # Validate Order Ownership
        # --------------------------------------

        if order.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "You do not have access to "
                    "this order."
                ),
            )

        # --------------------------------------
        # Prevent Payment For Completed Order
        # --------------------------------------

        if order.status == "paid":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "This order has already been "
                    "paid for."
                ),
            )

        # --------------------------------------
        # Validate Order Amount
        # --------------------------------------

        if order.total_amount <= Decimal("0.00"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Order total must be greater "
                    "than zero."
                ),
            )

        # --------------------------------------
        # Generate Payment Reference
        # --------------------------------------

        reference = (
            f"UK-{uuid4().hex}"
        )

        # --------------------------------------
        # Convert NGN To Kobo
        # --------------------------------------

        amount_in_kobo = int(
            order.total_amount * 100
        )

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
        # Paystack Request Headers
        # --------------------------------------

        headers = {
            "Authorization": (
                f"Bearer "
                f"{settings.PAYSTACK_SECRET_KEY}"
            ),
            "Content-Type": "application/json",
        }

        # --------------------------------------
        # Paystack Request Payload
        # --------------------------------------

        payload = {
            "email": user.email,
            "amount": amount_in_kobo,
            "reference": reference,
            "callback_url": (
                settings.PAYSTACK_CALLBACK_URL
            ),
            "currency": "NGN",
        }

        # --------------------------------------
        # Initialize Paystack Transaction
        # --------------------------------------

        try:
            response = httpx.post(
                (
                    f"{settings.PAYSTACK_BASE_URL}"
                    "/transaction/initialize"
                ),
                headers=headers,
                json=payload,
                timeout=30.0,
            )

        except httpx.RequestError:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
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
                    "Payment provider failed to "
                    "initialize the transaction."
                ),
            )

        # --------------------------------------
        # Parse Paystack Response
        # --------------------------------------

        try:
            response_data = response.json()

        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=(
                    "Invalid response from the "
                    "payment provider."
                ),
            )

        # --------------------------------------
        # Validate Paystack Response
        # --------------------------------------

        if not response_data.get("status"):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=(
                    response_data.get(
                        "message"
                    )
                    or
                    "Payment initialization "
                    "failed."
                ),
            )

        payment_data = response_data.get(
            "data"
        )

        if not payment_data:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=(
                    "Payment provider returned "
                    "invalid payment data."
                ),
            )

        # --------------------------------------
        # Return Payment Details
        # --------------------------------------

        return PaymentInitializeResponse(
            authorization_url=payment_data[
                "authorization_url"
            ],
            access_code=payment_data[
                "access_code"
            ],
            reference=payment_data[
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
        using its payment reference.
        """

        # --------------------------------------
        # Get Local Payment
        # --------------------------------------

        payment = (
            PaymentService.get_payment_by_reference(
                db,
                reference,
            )
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
        # Paystack Request Headers
        # --------------------------------------

        headers = {
            "Authorization": (
                f"Bearer "
                f"{settings.PAYSTACK_SECRET_KEY}"
            ),
        }

        # --------------------------------------
        # Verify With Paystack
        # --------------------------------------

        try:
            response = httpx.get(
                (
                    f"{settings.PAYSTACK_BASE_URL}"
                    f"/transaction/verify/"
                    f"{reference}"
                ),
                headers=headers,
                timeout=30.0,
            )

        except httpx.RequestError:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=(
                    "Unable to connect to the "
                    "payment provider."
                ),
            )

        # --------------------------------------
        # Handle Provider Error
        # --------------------------------------

        if response.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=(
                    "Payment provider failed to "
                    "verify the transaction."
                ),
            )

        # --------------------------------------
        # Parse Provider Response
        # --------------------------------------

        try:
            response_data = response.json()

        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=(
                    "Invalid response from the "
                    "payment provider."
                ),
            )

        # --------------------------------------
        # Validate Provider Response
        # --------------------------------------

        if not response_data.get("status"):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=(
                    response_data.get(
                        "message"
                    )
                    or
                    "Payment verification failed."
                ),
            )

        payment_data = response_data.get(
            "data"
        )

        if not payment_data:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=(
                    "Payment provider returned "
                    "invalid payment data."
                ),
            )

        # --------------------------------------
        # Validate Amount
        # --------------------------------------

        provider_amount = (
            Decimal(
                str(
                    payment_data["amount"]
                )
            )
            / Decimal("100")
        )

        if provider_amount != payment.amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Payment amount does not "
                    "match the order amount."
                ),
            )

        # --------------------------------------
        # Update Payment Record
        # --------------------------------------

        provider_status = payment_data.get(
            "status",
            "failed",
        )

        payment.status = provider_status

        payment.channel = payment_data.get(
            "channel"
        )

        provider_transaction_id = (
            payment_data.get("id")
        )

        if provider_transaction_id is not None:
            payment.provider_transaction_id = str(
                provider_transaction_id
            )

        # --------------------------------------
        # Update Order Status
        # --------------------------------------

        order = payment.order

        if provider_status == "success":
            order.status = "paid"

        elif provider_status == "failed":
            order.status = "payment_failed"

        # --------------------------------------
        # Save Changes
        # --------------------------------------

        db.commit()
        db.refresh(payment)

        # --------------------------------------
        # Parse Paid At
        # --------------------------------------

        paid_at = payment_data.get(
            "paid_at"
        )

        if paid_at is not None:
            try:
                paid_at = datetime.fromisoformat(
                    paid_at.replace(
                        "Z",
                        "+00:00",
                    )
                )

            except (
                ValueError,
                AttributeError,
            ):
                paid_at = None

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