from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.order import OrderResponse


class CustomerSummary(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class AdminPayment(BaseModel):
    reference: str
    status: str
    amount: Decimal
    currency: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminOrderDetail(OrderResponse):
    customer: CustomerSummary
    payment_status: str
    payments: list[AdminPayment]
    available_actions: list[str]
    product_names: dict[int, str]


class AdminOrderPage(BaseModel):
    items: list[AdminOrderDetail]
    total: int
    page: int
    page_size: int


class InventoryUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stock_quantity: int | None = Field(ge=0, le=2147483647, strict=True)
    in_stock: bool
    expected_stock_quantity: int | None = Field(ge=0, le=2147483647, strict=True)
    expected_in_stock: bool


class InventorySummary(BaseModel):
    total: int
    in_stock: int
    low_stock: int
    out_of_stock: int
    uncounted: int
    low_stock_threshold: int


class SalesSummary(BaseModel):
    verified_orders: int
    verified_sales_ngn: Decimal
    cancelled_verified_orders: int
    cancelled_verified_ngn: Decimal


class AdminOverview(BaseModel):
    inventory: InventorySummary
    total_orders: int
    awaiting_processing: int
    sales: SalesSummary
    recent_orders: list[AdminOrderDetail]


class AdminCustomer(CustomerSummary):
    order_count: int


class AdminCustomerPage(BaseModel):
    items: list[AdminCustomer]
    total: int
    page: int
    page_size: int
