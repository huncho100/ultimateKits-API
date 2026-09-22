import json
import logging

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    status,
)
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.database import get_db
from app.models.user import User
from app.schemas.payment import (
    PaymentInitializeResponse,
    PaymentVerificationResponse,
    PaymentWebhookResponse,
)
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService


logger = logging.getLogger(__name__)


# ==========================================
# Router
# ==========================================

router = APIRouter(
    prefix="/payments",
    tags=["Payments"],
)


# ==========================================
# Initialize Payment
# ==========================================

@router.post(
    "/initialize/{order_id}",
    response_model=PaymentInitializeResponse,
    status_code=status.HTTP_200_OK,
)
def initialize_payment(
    order_id: int,
    current_user: User = Depends(
        get_current_user,
    ),
    db: Session = Depends(get_db),
):
    """
    Initialize a Paystack payment transaction
    for an authenticated user's order.
    """

    # --------------------------------------
    # Get Order
    # --------------------------------------

    order = OrderService.get_order_by_id(
        db,
        order_id,
    )

    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found.",
        )

    # --------------------------------------
    # Initialize Payment
    # --------------------------------------

    return PaymentService.initialize_payment(
        db,
        order,
        current_user,
    )


# ==========================================
# Verify Payment
# ==========================================

@router.get(
    "/verify/{reference}",
    response_model=PaymentVerificationResponse,
)
def verify_payment(
    reference: str,
    current_user: User = Depends(
        get_current_user,
    ),
    db: Session = Depends(get_db),
):
    """
    Verify a Paystack payment transaction using
    its payment reference.
    """

    return PaymentService.verify_payment(
        db,
        reference,
        current_user,
    )


# ==========================================
# Paystack Webhook
# ==========================================

@router.post(
    "/webhook",
    response_model=PaymentWebhookResponse,
    status_code=status.HTTP_200_OK,
)
async def paystack_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Receive a Paystack transaction event.

    Without this, an order is only ever settled if the
    customer's browser makes it back to the callback page.
    A closed tab, a dropped connection or a payment
    completed on the bank's app leaves money taken and the
    order sitting unpaid.

    The endpoint is deliberately unauthenticated - Paystack
    cannot hold a user session - so authenticity rests
    entirely on the HMAC signature over the raw body.
    """

    raw_body = await request.body()

    # --------------------------------------
    # Verify Signature
    # --------------------------------------

    if not PaymentService.verify_webhook_signature(
        raw_body,
        request.headers.get("x-paystack-signature"),
    ):
        logger.warning(
            "Rejected Paystack webhook with an invalid "
            "signature.",
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature.",
        )

    # --------------------------------------
    # Parse Payload
    # --------------------------------------

    # Only parsed after the signature is confirmed, so an
    # unauthenticated caller cannot reach the parser.

    try:
        event = json.loads(raw_body)

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook payload.",
        ) from error

    if not isinstance(event, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook payload.",
        )

    # --------------------------------------
    # Apply Event
    # --------------------------------------

    # The session is synchronous, so the database work runs
    # off the event loop rather than blocking every other
    # request while it completes.

    outcome = await run_in_threadpool(
        PaymentService.handle_webhook_event,
        db,
        event,
    )

    return PaymentWebhookResponse(
        status="received",
        outcome=outcome,
    )