from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin
from app.core.statuses import ORDER_STATUSES
from app.database.database import get_db
from app.models.product import Product
from app.schemas.admin import AdminCustomerPage, AdminOrderPage, AdminOverview, InventoryUpdate
from app.schemas.product import ProductResponse
from app.services.admin_service import AdminService


router = APIRouter(
    prefix="/admin", tags=["Admin Management"],
    dependencies=[Depends(get_current_admin)],
)


@router.get("/overview", response_model=AdminOverview)
def overview(db: Session = Depends(get_db)):
    return AdminService.overview(db)


@router.get("/orders/page", response_model=AdminOrderPage)
def orders(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = Query(None, max_length=255),
    status: str | None = Query(None, max_length=50),
    payment_status: Literal["verified", "unverified"] | None = None,
    customer_id: int | None = Query(None, ge=1),
):
    if status is not None and status not in ORDER_STATUSES:
        raise HTTPException(422, "Unknown order status.")
    return AdminService.orders(
        db, page=page, page_size=page_size, q=q, status=status,
        payment_status=payment_status, customer_id=customer_id,
    )


@router.get("/customers", response_model=AdminCustomerPage)
def customers(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = Query(None, max_length=255),
):
    return AdminService.customers(db, page=page, page_size=page_size, q=q)


@router.put("/inventory/{product_id}", response_model=ProductResponse)
def update_inventory(
    product_id: int, data: InventoryUpdate, db: Session = Depends(get_db),
):
    product = db.query(Product).filter(Product.id == product_id).with_for_update().first()
    if product is None:
        raise HTTPException(404, "Product not found.")
    if (
        product.stock_quantity != data.expected_stock_quantity
        or product.in_stock != data.expected_in_stock
    ):
        raise HTTPException(409, "Stock changed since this page loaded. Reload before saving.")
    product.stock_quantity = data.stock_quantity
    product.in_stock = data.in_stock and data.stock_quantity != 0
    db.commit()
    db.refresh(product)
    return product
