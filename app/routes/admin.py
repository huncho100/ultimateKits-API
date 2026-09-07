from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin
from app.database.database import get_db
from app.models.order import Order
from app.models.user import User
from app.schemas.admin_order import (
    AdminOrderStatusResponse,
    AdminOrderStatusUpdate,
)
from app.schemas.order import OrderResponse
from app.services.admin_order_service import AdminOrderService


# ==========================================
# Router
# ==========================================

router = APIRouter(
    prefix="/admin/orders",
    tags=["Admin Orders"],
)


# ==========================================
# Get All Orders
# ==========================================

@router.get(
    "",
    response_model=list[OrderResponse],
)
def get_all_orders(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """
    Retrieve all customer orders.

    Administrator access required.
    """

    return AdminOrderService.get_all_orders(db)


# ==========================================
# Get Any Order
# ==========================================

@router.get(
    "/{order_id}",
    response_model=OrderResponse,
)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """
    Retrieve any order by ID.

    Administrator access required.
    """

    order = AdminOrderService.get_order_by_id(
        db,
        order_id,
    )

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found.",
        )

    return order


# ==========================================
# Update Order Status
# ==========================================

@router.patch(
    "/{order_id}",
    response_model=AdminOrderStatusResponse,
)
def update_order_status(
    order_id: int,
    data: AdminOrderStatusUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """
    Update the status of an order.

    Administrator access required.
    """

    order = AdminOrderService.get_order_by_id(
        db,
        order_id,
    )

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found.",
        )

    try:
        return AdminOrderService.update_order_status(
            db,
            order,
            data.status,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )