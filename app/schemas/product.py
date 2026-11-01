
from datetime import datetime
from decimal import Decimal
from urllib.parse import unquote, urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ==========================================
# Shared Product Validation
# ==========================================

def _validate_product_image_path(value: str | None) -> str | None:
    """
    Accept only local product image paths.

    Images must:
    - Use /images/products/
    - Have an approved image extension
    - Not contain query parameters or fragments
    - Not contain directory traversal sequences
    - Not reference external hosts
    """
    if value is None:
        return None

    parsed = urlsplit(value)
    decoded_path = unquote(parsed.path)

    allowed_extensions = {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".avif",
        ".gif",
    }

    if (
        not value.startswith("/images/products/")
        or parsed.netloc
        or parsed.query
        or parsed.fragment
        or "\\" in decoded_path
        or any(part == ".." for part in decoded_path.split("/"))
        or parsed.path.lower().rsplit(".", 1)[-1]
        not in {ext.lstrip(".") for ext in allowed_extensions}
    ):
        raise ValueError(
            "Product images must use a valid root-relative "
            "/images/products/ path with an approved image extension."
        )

    return value


def _validate_gallery_paths(
    value: list[str] | None,
) -> list[str] | None:
    if value is None:
        return None

    validated = [
        _validate_product_image_path(path)
        for path in value
    ]

    if len(validated) != len(set(validated)):
        raise ValueError("Product gallery paths must be unique.")

    return validated


class ProductInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator(
        "name",
        "sport",
        "category",
        check_fields=False,
    )
    @classmethod
    def meaningful_text(cls, value: str | None) -> str | None:
        if value is not None:
            value = value.strip()

            if len(value) < 2:
                raise ValueError(
                    "Must contain at least two non-whitespace characters."
                )

        return value

    @field_validator("image", check_fields=False)
    @classmethod
    def validate_image_path(
        cls,
        value: str | None,
    ) -> str | None:
        return _validate_product_image_path(value)

    @field_validator("gallery", check_fields=False)
    @classmethod
    def validate_gallery_paths(
        cls,
        value: list[str] | None,
    ) -> list[str] | None:
        return _validate_gallery_paths(value)


# ==========================================
# Product Create
# ==========================================

class ProductCreate(ProductInput):
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

    gallery: list[str] = Field(
        default_factory=list,
    )

    is_featured: bool = False

    is_new: bool = False

    is_best_seller: bool = False

    in_stock: bool = True

    stock_quantity: int | None = Field(
        default=None,
        ge=0,
        le=2147483647,
        strict=True,
    )


# ==========================================
# Product Update
# ==========================================

class ProductUpdate(ProductInput):
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

    gallery: list[str] | None = None

    is_featured: bool | None = None

    is_new: bool | None = None

    is_best_seller: bool | None = None

    in_stock: bool | None = None

    stock_quantity: int | None = Field(
        default=None,
        ge=0,
        le=2147483647,
        strict=True,
    )

    @field_validator("price")
    @classmethod
    def validate_price(cls, value: Decimal | None) -> Decimal:
        if value is None:
            raise ValueError("A product price cannot be null.")

        return value


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

    description: str | None = None

    price: Decimal

    development_placeholder: bool = False

    old_price: Decimal | None

    rating: float

    image: str | None

    gallery: list[str] = Field(default_factory=list)

    is_featured: bool

    is_new: bool

    is_best_seller: bool

    in_stock: bool

    stock_quantity: int | None = None

    created_at: datetime

    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )
