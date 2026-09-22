from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import settings


# ==========================================
# Cart Item Schemas
# ==========================================

class CartItemCreate(BaseModel):
    """
    Data required to add a product to a cart.
    """

    product_id: int = Field(
        gt=0,
    )

    quantity: int = Field(
        gt=0,
        le=settings.MAX_CART_ITEM_QUANTITY,
    )


class CartItemUpdate(BaseModel):
    """
    Data used to update an existing cart item.
    """

    quantity: int = Field(
        gt=0,
        le=settings.MAX_CART_ITEM_QUANTITY,
    )


class CartSyncRequest(BaseModel):
    items: list[CartItemCreate] = Field(
        default_factory=list,
        max_length=100,
    )


class CartItemResponse(BaseModel):
    """
    Cart item returned by the API.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    cart_id: int
    product_id: int
    quantity: int
    unit_price: Decimal
    subtotal: Decimal


# ==========================================
# Cart Schemas
# ==========================================

class CartCreate(BaseModel):
    """
    Data required to create a cart.
    """

    user_id: int = Field(
        gt=0,
    )


class CartResponse(BaseModel):
    """
    Cart returned by the API.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    items: list[CartItemResponse] = Field(
        default_factory=list,
    )


# ==========================================
# Cart Summary
# ==========================================

class CartSummaryResponse(BaseModel):
    """
    Cart summary containing item count and total.
    """

    cart_id: int
    user_id: int
    item_count: int
    total_amount: Decimal