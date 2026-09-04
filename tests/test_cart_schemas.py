from datetime import datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.cart import (
    CartCreate,
    CartItemCreate,
    CartItemResponse,
    CartItemUpdate,
    CartResponse,
    CartSummaryResponse,
)


# ==========================================
# CartItemCreate
# ==========================================

def test_cart_item_create_valid():
    data = CartItemCreate(
        product_id=1,
        quantity=2,
    )

    assert data.product_id == 1
    assert data.quantity == 2

    print("✓ CartItemCreate valid test passed")


def test_cart_item_create_rejects_invalid_product_id():
    with pytest.raises(ValidationError):
        CartItemCreate(
            product_id=0,
            quantity=2,
        )

    print("✓ CartItemCreate invalid product ID test passed")


def test_cart_item_create_rejects_invalid_quantity():
    with pytest.raises(ValidationError):
        CartItemCreate(
            product_id=1,
            quantity=0,
        )

    print("✓ CartItemCreate invalid quantity test passed")


# ==========================================
# CartItemUpdate
# ==========================================

def test_cart_item_update_valid():
    data = CartItemUpdate(
        quantity=5,
    )

    assert data.quantity == 5

    print("✓ CartItemUpdate valid test passed")


def test_cart_item_update_rejects_invalid_quantity():
    with pytest.raises(ValidationError):
        CartItemUpdate(
            quantity=0,
        )

    print("✓ CartItemUpdate invalid quantity test passed")


# ==========================================
# CartItemResponse
# ==========================================

def test_cart_item_response_valid():
    data = CartItemResponse(
        id=1,
        cart_id=10,
        product_id=25,
        quantity=2,
        unit_price=Decimal("89.99"),
        subtotal=Decimal("179.98"),
    )

    assert data.id == 1
    assert data.cart_id == 10
    assert data.product_id == 25
    assert data.quantity == 2
    assert data.unit_price == Decimal("89.99")
    assert data.subtotal == Decimal("179.98")

    print("✓ CartItemResponse valid test passed")


# ==========================================
# CartCreate
# ==========================================

def test_cart_create_valid():
    data = CartCreate(
        user_id=1,
    )

    assert data.user_id == 1

    print("✓ CartCreate valid test passed")


def test_cart_create_rejects_invalid_user_id():
    with pytest.raises(ValidationError):
        CartCreate(
            user_id=0,
        )

    print("✓ CartCreate invalid user ID test passed")


# ==========================================
# CartResponse
# ==========================================

def test_cart_response_valid():
    created_at = datetime.now()
    updated_at = datetime.now()

    item = CartItemResponse(
        id=1,
        cart_id=10,
        product_id=25,
        quantity=2,
        unit_price=Decimal("89.99"),
        subtotal=Decimal("179.98"),
    )

    data = CartResponse(
        id=10,
        user_id=1,
        created_at=created_at,
        updated_at=updated_at,
        items=[item],
    )

    assert data.id == 10
    assert data.user_id == 1
    assert data.created_at == created_at
    assert data.updated_at == updated_at
    assert len(data.items) == 1
    assert data.items[0].product_id == 25

    print("✓ CartResponse valid test passed")


def test_cart_response_defaults_to_empty_items():
    now = datetime.now()

    data = CartResponse(
        id=10,
        user_id=1,
        created_at=now,
        updated_at=now,
    )

    assert data.items == []

    print("✓ CartResponse empty items test passed")


# ==========================================
# CartSummaryResponse
# ==========================================

def test_cart_summary_response_valid():
    data = CartSummaryResponse(
        cart_id=10,
        user_id=1,
        item_count=3,
        total_amount=Decimal("249.97"),
    )

    assert data.cart_id == 10
    assert data.user_id == 1
    assert data.item_count == 3
    assert data.total_amount == Decimal("249.97")

    print("✓ CartSummaryResponse valid test passed")


# ==========================================
# Decimal Serialization
# ==========================================

def test_cart_item_response_decimal_serialization():
    data = CartItemResponse(
        id=1,
        cart_id=10,
        product_id=25,
        quantity=2,
        unit_price=Decimal("89.99"),
        subtotal=Decimal("179.98"),
    )

    dumped = data.model_dump()

    assert dumped["unit_price"] == Decimal("89.99")
    assert dumped["subtotal"] == Decimal("179.98")

    print("✓ Cart decimal serialization test passed")