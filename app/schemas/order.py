from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


# ==========================================
# Order Item Response
# ==========================================

class OrderItemResponse(BaseModel):
    """
    Response schema for an item belonging
    to an order.
    """

    id: int
    order_id: int
    product_id: int

    quantity: int
    unit_price: Decimal
    subtotal: Decimal

    model_config = ConfigDict(
        from_attributes=True,
    )


# ==========================================
# Order Response
# ==========================================

class OrderResponse(BaseModel):
    """
    Response schema for an order.
    """

    id: int
    user_id: int

    status: str
    total_amount: Decimal

    created_at: datetime
    updated_at: datetime

    items: list[OrderItemResponse] = []

    model_config = ConfigDict(
        from_attributes=True,
    )