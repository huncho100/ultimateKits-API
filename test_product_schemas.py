from datetime import datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.product import (
    ProductCreate,
    ProductResponse,
    ProductUpdate,
)


# ==========================================
# Valid Product Data
# ==========================================

VALID_PRODUCT = {
    "name": "Manchester United Home Jersey",
    "sport": "Football",
    "category": "Jerseys",
    "team": "Manchester United",
    "league": "Premier League",
    "brand": "Adidas",
    "price": Decimal("89.99"),
    "old_price": Decimal("109.99"),
    "rating": 4.5,
    "image": "/images/manchester-united-home.jpg",
    "is_featured": True,
    "is_new": True,
    "is_best_seller": False,
    "in_stock": True,
}


# ==========================================
# ProductCreate
# ==========================================

def test_product_create_valid():
    product = ProductCreate(**VALID_PRODUCT)

    assert product.name == "Manchester United Home Jersey"
    assert product.sport == "Football"
    assert product.category == "Jerseys"
    assert product.team == "Manchester United"
    assert product.league == "Premier League"
    assert product.brand == "Adidas"
    assert product.price == Decimal("89.99")
    assert product.old_price == Decimal("109.99")
    assert product.rating == 4.5
    assert product.is_featured is True
    assert product.is_new is True
    assert product.in_stock is True


def test_product_create_optional_fields():
    product = ProductCreate(
        name="Generic Training Jersey",
        sport="Football",
        category="Training",
        price=Decimal("49.99"),
    )

    assert product.team is None
    assert product.league is None
    assert product.brand is None
    assert product.old_price is None
    assert product.image is None


def test_product_create_defaults():
    product = ProductCreate(
        name="Basic Jersey",
        sport="Football",
        category="Jerseys",
        price=Decimal("50.00"),
    )

    assert product.rating == 0
    assert product.is_featured is False
    assert product.is_new is False
    assert product.is_best_seller is False
    assert product.in_stock is True


# ==========================================
# ProductCreate Validation
# ==========================================

def test_product_create_rejects_negative_price():
    with pytest.raises(ValidationError):
        ProductCreate(
            name="Invalid Product",
            sport="Football",
            category="Jerseys",
            price=Decimal("-10.00"),
        )


def test_product_create_rejects_zero_price():
    with pytest.raises(ValidationError):
        ProductCreate(
            name="Invalid Product",
            sport="Football",
            category="Jerseys",
            price=Decimal("0.00"),
        )


def test_product_create_rejects_rating_above_five():
    with pytest.raises(ValidationError):
        ProductCreate(
            name="Invalid Product",
            sport="Football",
            category="Jerseys",
            price=Decimal("50.00"),
            rating=5.1,
        )


def test_product_create_rejects_negative_rating():
    with pytest.raises(ValidationError):
        ProductCreate(
            name="Invalid Product",
            sport="Football",
            category="Jerseys",
            price=Decimal("50.00"),
            rating=-0.1,
        )


def test_product_create_rejects_short_name():
    with pytest.raises(ValidationError):
        ProductCreate(
            name="A",
            sport="Football",
            category="Jerseys",
            price=Decimal("50.00"),
        )


def test_product_create_requires_name():
    with pytest.raises(ValidationError):
        ProductCreate(
            sport="Football",
            category="Jerseys",
            price=Decimal("50.00"),
        )


def test_product_create_requires_price():
    with pytest.raises(ValidationError):
        ProductCreate(
            name="Test Jersey",
            sport="Football",
            category="Jerseys",
        )


# ==========================================
# ProductUpdate
# ==========================================

def test_product_update_partial_update():
    product = ProductUpdate(
        price=Decimal("79.99"),
        in_stock=False,
    )

    assert product.price == Decimal("79.99")
    assert product.in_stock is False

    assert product.name is None
    assert product.sport is None
    assert product.category is None


def test_product_update_all_fields_optional():
    product = ProductUpdate()

    assert product.name is None
    assert product.sport is None
    assert product.category is None
    assert product.team is None
    assert product.league is None
    assert product.brand is None
    assert product.price is None
    assert product.old_price is None
    assert product.rating is None
    assert product.image is None
    assert product.is_featured is None
    assert product.is_new is None
    assert product.is_best_seller is None
    assert product.in_stock is None


def test_product_update_rejects_invalid_price():
    with pytest.raises(ValidationError):
        ProductUpdate(
            price=Decimal("-1.00"),
        )


def test_product_update_rejects_invalid_rating():
    with pytest.raises(ValidationError):
        ProductUpdate(
            rating=6,
        )


# ==========================================
# ProductResponse
# ==========================================

def test_product_response_valid():
    now = datetime.now()

    product = ProductResponse(
        id=1,
        **VALID_PRODUCT,
        created_at=now,
        updated_at=now,
    )

    assert product.id == 1
    assert product.name == "Manchester United Home Jersey"
    assert product.price == Decimal("89.99")
    assert product.rating == 4.5
    assert product.created_at == now
    assert product.updated_at == now


def test_product_response_from_attributes():
    """
    Verify ProductResponse can be created from an
    object with SQLAlchemy-style attributes.
    """

    now = datetime.now()

    class FakeProduct:
        id = 1
        name = "Lakers White Jersey"
        sport = "Basketball"
        category = "Jerseys"
        team = "Los Angeles Lakers"
        league = "NBA"
        brand = "Nike"
        price = Decimal("99.99")
        old_price = Decimal("119.99")
        rating = 4.8
        image = "/images/lakers-white.jpg"
        is_featured = True
        is_new = False
        is_best_seller = True
        in_stock = True
        created_at = now
        updated_at = now

    product = ProductResponse.model_validate(
        FakeProduct()
    )

    assert product.id == 1
    assert product.name == "Lakers White Jersey"
    assert product.team == "Los Angeles Lakers"
    assert product.price == Decimal("99.99")
    assert product.is_best_seller is True


# ==========================================
# Schema Serialization
# ==========================================

def test_product_response_serialization():
    now = datetime.now()

    product = ProductResponse(
        id=1,
        **VALID_PRODUCT,
        created_at=now,
        updated_at=now,
    )

    data = product.model_dump()

    assert data["id"] == 1
    assert data["name"] == "Manchester United Home Jersey"
    assert data["price"] == Decimal("89.99")
    assert data["rating"] == 4.5
    assert data["is_featured"] is True