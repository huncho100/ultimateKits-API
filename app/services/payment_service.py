import hashlib
import hmac
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Final
from uuid import uuid4

import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.statuses import (
    OrderStatus,
    PaymentStatus,
    can_transition,
)
from app.models.order import Order
from app.models.payment import Payment
from app.models.user import User
from app.schemas.payment import (
    PaymentInitializeResponse,
    PaymentVerificationResponse,
)
from app.services.cart_service import CartService
from app.services.inventory_service import InventoryService


logger = logging.getLogger(__name__)


# Paystack webhook events that settle a transaction. Every
# other event is acknowledged and ignored rather than guessed
# at, so an unfamiliar event can never move money.
SETTLEMENT_EVENTS: Final = frozenset({"charge.success"})


class ProviderResultMismatch(Exception):
    """
    The provider described a transaction that does not match
    the local payment it claims to settle.

    This is never recoverable by retrying and must never
    result in an order being marked paid.
    """


def _provider_amount_to_major_units(
    raw_amount: Any,
) -> Decimal | None:
    """
    Convert a provider amount in minor units (kobo) to the
    major unit (naira).

    Returns None when the value is absent or unusable, which
    callers treat as a mismatch rather than as a zero.
    """

    if raw_amount is None:
        return None

    try:
        return (
            Decimal(str(raw_amount))
            / Decimal("100")
        ).quantize(Decimal("0.01"))

    except (InvalidOperation, TypeError, ValueError):
        return None


def _assert_provider_result_matches(
    payment: Payment,
    payment_data: dict[str, Any],
) -> None:
    """
    Confirm the provider is describing the transaction we
    think it is.

    Amount and currency are checked independently. Checking
    only the number would accept a transaction settled in a
    different currency - 100 of a stronger unit is not 100
    naira - and a missing field is treated as a mismatch
    rather than assumed to agree.
    """

    provider_amount = _provider_amount_to_major_units(
        payment_data.get("amount"),
    )

    if (
        provider_amount is None
        or provider_amount != payment.amount
    ):
        raise ProviderResultMismatch(
            "Payment amount does not match "
            "the order amount."
        )

    provider_currency = payment_data.get("currency")

    if (
        not isinstance(provider_currency, str)
        or provider_currency.upper()
        != payment.currency.upper()
    ):
        raise ProviderResultMismatch(
            "Payment currency does not match "
            "the order currency."
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
        Retrieve the payment that represents an order.

        An order can accumulate more than one payment row
        when a customer restarts checkout, so a successful
        payment is preferred over a newer unsuccessful one.
        Ordering purely by date would report an order that
        has been paid for as still awaiting payment.
        """

        return (
            db.query(Payment)
            .filter(
                Payment.order_id == order_id,
            )
            .order_by(
                (
                    Payment.status
                    == PaymentStatus.SUCCESS
                ).desc(),
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

        if order.status == OrderStatus.PAID:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "This order has already been "
                    "paid for."
                ),
            )

        # --------------------------------------
        # Prevent Payment For Unpayable Order
        # --------------------------------------

        # Cancelled orders, and orders already being
        # fulfilled, cannot reach "paid". Taking money for one
        # would leave the customer charged for something this
        # system will never act on.

        if not can_transition(
            order.status,
            OrderStatus.PAID,
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "This order can no longer "
                    "be paid for."
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
        # Supersede Abandoned Attempts
        # --------------------------------------

        # Every click of "pay" used to mint another payment
        # row and another reference, all of them pending
        # forever. Retiring the previous attempts keeps at
        # most one reference live per order, so the order's
        # payment state stays answerable. The old rows are
        # kept rather than deleted: the customer may still
        # have that Paystack page open, and if they pay it
        # the settlement path has a record to match against.

        superseded = (
            db.query(Payment)
            .filter(
                Payment.order_id == order.id,
                Payment.status == PaymentStatus.PENDING,
            )
            .all()
        )

        for stale_payment in superseded:
            stale_payment.status = PaymentStatus.ABANDONED

        # --------------------------------------
        # Generate Payment Reference
        # --------------------------------------

        reference = (
            f"UK-{uuid4().hex}"
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
            status=PaymentStatus.PENDING,
        )

        db.add(payment)
        db.commit()
        db.refresh(payment)

        # --------------------------------------
        # Request Authorization
        # --------------------------------------

        # The provider call is a separate method so that a
        # failure anywhere in it - connection, HTTP status,
        # unparseable body, provider-reported error - lands
        # in one place. Otherwise the row just created would
        # be left pending by whichever branch raised, and
        # nothing would ever settle it.

        try:
            return PaymentService._request_authorization(
                payment,
                user,
            )

        except HTTPException:
            payment.status = PaymentStatus.FAILED

            db.commit()

            logger.warning(
                "Paystack initialization failed for payment "
                "%s; marked failed.",
                payment.reference,
            )

            raise

    # ==========================================
    # Request Authorization
    # ==========================================

    @staticmethod
    def _request_authorization(
        payment: Payment,
        user: User,
    ) -> PaymentInitializeResponse:
        """
        Ask Paystack to open a transaction for a payment that
        has already been recorded locally.
        """

        # --------------------------------------
        # Convert To Minor Units
        # --------------------------------------

        # Derived from the stored payment rather than from
        # the order, so the amount and currency we send are
        # the same values verification later compares the
        # provider's answer against.

        amount_in_kobo = int(
            payment.amount * 100
        )

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
            "reference": payment.reference,
            "callback_url": (
                settings.PAYSTACK_CALLBACK_URL
            ),
            "currency": payment.currency,
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
        # Settle
        # --------------------------------------

        try:
            PaymentService.settle_payment(
                db,
                payment,
                payment_data,
            )

        except ProviderResultMismatch as error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(error),
            ) from error

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

    # ==========================================
    # Settle Payment
    # ==========================================

    @staticmethod
    def settle_payment(
        db: Session,
        payment: Payment,
        payment_data: dict[str, Any],
    ) -> Payment:
        """
        Apply a provider result to a payment and its order.

        This is the single place a transaction is settled.
        The customer-returning-from-checkout path and the
        Paystack webhook both call it, so an order reaches
        the same state no matter which arrives first, or
        whether both do.

        Raises ProviderResultMismatch when the provider's
        amount or currency disagrees with the local record.
        Nothing is written in that case.
        """

        _assert_provider_result_matches(
            payment,
            payment_data,
        )

        provider_status = (
            payment_data.get("status")
            or PaymentStatus.FAILED
        )

        # A settled success is final. A duplicate, delayed or
        # replayed event must never move an order back out of
        # "paid" once the money has been taken.
        if (
            payment.status == PaymentStatus.SUCCESS
            and provider_status != PaymentStatus.SUCCESS
        ):
            logger.warning(
                "Ignoring %s result for already successful "
                "payment %s.",
                provider_status,
                payment.reference,
            )

            return payment

        payment.status = provider_status

        channel = payment_data.get("channel")

        if channel is not None:
            payment.channel = channel

        provider_transaction_id = payment_data.get("id")

        if provider_transaction_id is not None:
            payment.provider_transaction_id = str(
                provider_transaction_id
            )

        if provider_status == PaymentStatus.SUCCESS:
            PaymentService._abandon_sibling_payments(
                db,
                payment,
            )

        order = payment.order

        if order is not None:
            PaymentService._apply_result_to_order(
                db,
                order,
                provider_status,
            )

        db.commit()
        db.refresh(payment)

        return payment

    # ==========================================
    # Abandon Sibling Payments
    # ==========================================

    @staticmethod
    def _abandon_sibling_payments(
        db: Session,
        payment: Payment,
    ) -> None:
        """
        Retire the order's other unresolved payments once one
        of them has succeeded.

        Without this, a reference the customer opened but
        never used stays pending against an order that has
        already been paid for, and the order looks like it is
        still waiting for money.
        """

        (
            db.query(Payment)
            .filter(
                Payment.order_id == payment.order_id,
                Payment.id != payment.id,
                Payment.status == PaymentStatus.PENDING,
            )
            .update(
                {
                    Payment.status: (
                        PaymentStatus.ABANDONED
                    ),
                },
                synchronize_session="fetch",
            )
        )

    # ==========================================
    # Apply Result To Order
    # ==========================================

    @staticmethod
    def _apply_result_to_order(
        db: Session,
        order: Order,
        provider_status: str,
    ) -> None:
        """
        Move an order in response to a payment result.

        The move is checked against the order state machine
        rather than assigned outright. An order an operator
        has already begun fulfilling must not be dragged back
        to "paid" by a webhook that arrives late, and a
        cancelled order must not quietly become live again.

        A provider status this system does not recognise
        leaves the order alone.
        """

        target_status = {
            PaymentStatus.SUCCESS: OrderStatus.PAID,
            PaymentStatus.FAILED: (
                OrderStatus.PAYMENT_FAILED
            ),
        }.get(provider_status)

        if target_status is None:
            logger.warning(
                "Order %s left at '%s': unrecognised "
                "payment result '%s'.",
                order.id,
                order.status,
                provider_status,
            )

            return

        if not can_transition(
            order.status,
            target_status,
        ):
            logger.warning(
                "Order %s left at '%s': a '%s' payment "
                "result cannot move it to '%s'.",
                order.id,
                order.status,
                provider_status,
                target_status,
            )

            return

        was_already_paid = (
            order.status == OrderStatus.PAID
        )

        order.status = target_status

        # Stock leaves the shelf, and the cart is emptied,
        # only once the money has actually arrived. Doing
        # either at order creation would penalise a customer
        # whose card is about to be declined. The guard
        # matters: a replayed success for an order that was
        # already paid would otherwise decrement stock twice
        # and wipe whatever the customer has put in their
        # cart since.

        if (
            target_status == OrderStatus.PAID
            and not was_already_paid
        ):
            InventoryService.consume_for_order(
                db,
                order,
            )

            CartService.discard_items_for_user(
                db,
                order.user_id,
            )

    # ==========================================
    # Webhook Signature
    # ==========================================

    @staticmethod
    def verify_webhook_signature(
        raw_body: bytes,
        signature: str | None,
    ) -> bool:
        """
        Verify a Paystack webhook signature.

        Paystack signs the exact bytes of the request body
        with HMAC-SHA512 keyed on the secret key, so the raw
        body has to be used - re-serialising the parsed JSON
        would change the bytes and break the comparison.

        Comparison is constant time: a byte-by-byte check
        leaks, through timing, how much of a forged signature
        was correct.
        """

        if not signature:
            return False

        expected = hmac.new(
            settings.PAYSTACK_SECRET_KEY.encode("utf-8"),
            raw_body,
            hashlib.sha512,
        ).hexdigest()

        return hmac.compare_digest(expected, signature)

    # ==========================================
    # Handle Webhook Event
    # ==========================================

    @staticmethod
    def handle_webhook_event(
        db: Session,
        event: dict[str, Any],
    ) -> str:
        """
        Apply an already-authenticated Paystack event.

        Returns a short outcome for the response body and the
        logs. Nothing here raises for an event we choose not
        to act on: Paystack retries anything it does not see
        acknowledged, so an unrecognised event must still be
        answered 200.
        """

        event_name = event.get("event")

        data = event.get("data")

        if not isinstance(data, dict):
            data = {}

        if event_name not in SETTLEMENT_EVENTS:
            logger.info(
                "Ignoring Paystack event %s.",
                event_name,
            )

            return "ignored"

        reference = data.get("reference")

        if not reference or not isinstance(reference, str):
            logger.warning(
                "Paystack event %s carried no usable "
                "reference.",
                event_name,
            )

            return "ignored"

        payment = PaymentService.get_payment_by_reference(
            db,
            reference,
        )

        if payment is None:
            # Not one of ours. Acknowledged so Paystack stops
            # retrying, but never acted on.
            logger.warning(
                "Paystack event %s referenced unknown "
                "payment reference.",
                event_name,
            )

            return "unknown"

        if payment.status == PaymentStatus.SUCCESS:
            return "already_settled"

        try:
            PaymentService.settle_payment(
                db,
                payment,
                data,
            )

        except ProviderResultMismatch as error:
            # The signature was valid, so this came from
            # Paystack, yet it does not describe our payment.
            # That needs a human, and the order stays unpaid.
            logger.critical(
                "Refusing to settle payment %s from webhook: "
                "%s",
                payment.reference,
                error,
            )

            return "mismatch"

        return "settled"