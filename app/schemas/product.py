from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


# ==========================================
# Product Create
# ==========================================

class ProductCreate(BaseModel):
    """
    Schema used when creating a new product.
    """

    name: str = Field(
        ...,
        min_length=2,
        max_length=255,
    )

    sport: str = Field(
        ...,
        min_length=2,
        max_length=100,
    )

    category: str = Field(
        ...,
        min_length=2,
        max_length=100,
    )

    team: str | None = Field(
        default=None,
        max_length=150,
    )

    league: str | None = Field(
        default=None,
        max_length=150,
    )

    brand: str | None = Field(
        default=None,
        max_length=100,
    )

    price: Decimal = Field(
        ...,
        gt=0,
        decimal_places=2,
        max_digits=10,
    )

    old_price: Decimal | None = Field(
        default=None,
        gt=0,
        decimal_places=2,
        max_digits=10,
    )

    rating: float = Field(
        default=0,
        ge=0,
        le=5,
    )

    image: str | None = Field(
        default=None,
        max_length=500,
    )

    is_featured: bool = False

    is_new: bool = False

    is_best_seller: bool = False

    in_stock: bool = True


# ==========================================
# Product Update
# ==========================================

class ProductUpdate(BaseModel):
    """
    Schema used when updating an existing product.

    All fields are optional because updates may
    modify only part of a product.
    """

    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=255,
    )

    sport: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
    )

    category: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
    )

    team: str | None = Field(
        default=None,
        max_length=150,
    )

    league: str | None = Field(
        default=None,
        max_length=150,
    )

    brand: str | None = Field(
        default=None,
        max_length=100,
    )

    price: Decimal | None = Field(
        default=None,
        gt=0,
        decimal_places=2,
        max_digits=10,
    )

    old_price: Decimal | None = Field(
        default=None,
        gt=0,
        decimal_places=2,
        max_digits=10,
    )

    rating: float | None = Field(
        default=None,
        ge=0,
        le=5,
    )

    image: str | None = Field(
        default=None,
        max_length=500,
    )

    is_featured: bool | None = None

    is_new: bool | None = None

    is_best_seller: bool | None = None

    in_stock: bool | None = None


# ==========================================
# Product Response
# ==========================================

class ProductResponse(BaseModel):
    """
    Schema returned by the API when exposing
    product information.
    """

    id: int

    name: str

    sport: str

    category: str

    team: str | None

    league: str | None

    brand: str | None

    price: Decimal

    old_price: Decimal | None

    rating: float

    image: str | None

    is_featured: bool

    is_new: bool

    is_best_seller: bool

    in_stock: bool

    created_at: datetime

    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )