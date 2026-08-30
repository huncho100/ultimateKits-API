from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.database import get_db
from app.models.user import User
from app.schemas.order import OrderResponse
from app.services.order_service import OrderService


# ==========================================
# Router
# ==========================================

router = APIRouter(
    prefix="/orders",
    tags=["Orders"],
)


# ==========================================
# Create Order / Checkout
# ==========================================

@router.post(
    "",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_order(
    current_user: User = Depends(
        get_current_user,
    ),
    db: Session = Depends(get_db),
):
    """
    Create an order from the authenticated
    user's current cart.
    """

    return OrderService.create_order_from_cart(
        db,
        current_user.id,
    )


# ==========================================
# Get Current User Orders
# ==========================================

@router.get(
    "",
    response_model=list[OrderResponse],
)
def get_orders(
    current_user: User = Depends(
        get_current_user,
    ),
    db: Session = Depends(get_db),
):
    """
    Retrieve all orders belonging to the
    authenticated user.
    """

    return OrderService.get_user_orders(
        db,
        current_user.id,
    )


# ==========================================
# Get Order By ID
# ==========================================

@router.get(
    "/{order_id}",
    response_model=OrderResponse,
)
def get_order(
    order_id: int,
    current_user: User = Depends(
        get_current_user,
    ),
    db: Session = Depends(get_db),
):
    """
    Retrieve a specific order belonging to
    the authenticated user.
    """

    order = OrderService.get_order_by_id(
        db,
        order_id,
    )

    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found.",
        )

    # ------------------------------------------
    # Prevent Users From Accessing Another
    # User's Order
    # ------------------------------------------

    if order.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this order.",
        )

    return order