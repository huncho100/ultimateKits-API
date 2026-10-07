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

    # Omit to publish no description. The product page
    # says so plainly rather than showing invented copy.
    description: str | None = Field(
        default=None,
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

    # Leave unset to keep the product uncounted, where
    # in_stock alone decides availability. Give it a number
    # to have that number enforced.
    stock_quantity: int | None = Field(
        default=None,
        ge=0,
    )


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

    # Send null to withdraw a published description and
    # return the product to the empty state.
    description: str | None = Field(
        default=None,
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

    stock_quantity: int | None = Field(
        default=None,
        ge=0,
    )


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

    # Defaulted rather than merely nullable, for the same
    # reason as stock_quantity below: a product with no
    # published description leaves this out entirely, so
    # omitting it must not be a validation error.
    description: str | None = None

    price: Decimal

    old_price: Decimal | None

    rating: float

    image: str | None

    is_featured: bool

    is_new: bool

    is_best_seller: bool

    in_stock: bool

    # Defaulted rather than merely nullable: an uncounted
    # product is represented by leaving this out entirely,
    # so omitting it must not be a validation error.
    stock_quantity: int | None = None

    created_at: datetime

    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )