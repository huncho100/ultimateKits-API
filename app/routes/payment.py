from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.database import get_db
from app.models.user import User
from app.schemas.payment import (
    PaymentInitializeResponse,
    PaymentVerificationResponse,
)
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService


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