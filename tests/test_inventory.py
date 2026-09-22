"""
Stock counting.

Products are only counted when they have been given a
stock_quantity. A product left uncounted must behave exactly
as it did before counting existed, so several of these tests
exist to prove the absence of a change.
"""

import uuid
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.models.order import Order
from app.models.payment import Payment
from app.models.product import Product
from app.models.user import User
from app.schemas.cart import CartItemCreate, CartItemUpdate
from app.services.cart_service import CartService
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService


# ==========================================
# Test Helpers
# ==========================================

def create_test_user(db: Session) -> User:
    user = User(
        first_name="Stock",
        last_name="Customer",
        email=(
            f"stock_{uuid.uuid4().hex[:10]}"
            "@example.com"
        ),
        password_hash="test-password-hash",
        role="customer",
        is_active=True,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def create_test_product(
    db: Session,
    *,
    price: Decimal = Decimal("50.00"),
    in_stock: bool = True,
    stock_quantity: int | None = None,
) -> Product:
    product = Product(
        name=f"Stock Jersey {uuid.uuid4().hex[:6]}",
        sport="Football",
        category="Jerseys",
        team="Test Team",
        league="Test League",
        brand="Test Brand",
        price=price,
        old_price=None,
        rating=Decimal("4.50"),
        image=None,
        is_featured=False,
        is_new=False,
        is_best_seller=False,
        in_stock=in_stock,
        stock_quantity=stock_quantity,
    )

    db.add(product)
    db.commit()
    db.refresh(product)

    return product


def create_cart_with(
    db: Session,
    user: User,
    product: Product,
    quantity: int,
) -> Cart:
    cart = Cart(user_id=user.id)

    db.add(cart)
    db.commit()
    db.refresh(cart)

    db.add(
        CartItem(
            cart_id=cart.id,
            product_id=product.id,
            quantity=quantity,
        )
    )

    db.commit()
    db.refresh(cart)

    return cart


def settle(
    db: Session,
    user: User,
    order: Order,
    *,
    status: str = "success",
) -> Payment:
    payment = Payment(
        order_id=order.id,
        user_id=user.id,
        provider="paystack",
        reference=f"UK-STOCK-{uuid.uuid4().hex}",
        amount=order.total_amount,
        currency="NGN",
        status="pending",
    )

    db.add(payment)
    db.commit()
    db.refresh(payment)

    PaymentService.settle_payment(
        db,
        payment,
        {
            "reference": payment.reference,
            "amount": int(payment.amount * 100),
            "currency": "NGN",
            "status": status,
            "channel": "card",
            "id": 555_001,
        },
    )

    return payment


# ==========================================
# Uncounted Products Are Unchanged
# ==========================================

def test_uncounted_product_has_no_quantity_limit(
    db: Session,
):
    """
    A product without a stock_quantity is governed by
    in_stock alone, as it was before counting existed.
    """

    user = create_test_user(db)

    product = create_test_product(db)

    assert product.stock_quantity is None

    cart = CartService.get_or_create_cart(db, user.id)

    item = CartService.add_item(
        db,
        cart,
        CartItemCreate(
            product_id=product.id,
            quantity=50,
        ),
    )

    assert item.quantity == 50


def test_uncounted_product_is_not_decremented(
    db: Session,
):
    user = create_test_user(db)

    product = create_test_product(db)

    create_cart_with(db, user, product, 2)

    order = OrderService.create_order_from_cart(
        db,
        user.id,
    )

    settle(db, user, order)

    db.refresh(product)

    assert product.stock_quantity is None
    assert product.in_stock is True


def test_out_of_stock_flag_still_blocks_the_cart(
    db: Session,
):
    user = create_test_user(db)

    product = create_test_product(
        db,
        in_stock=False,
    )

    cart = CartService.get_or_create_cart(db, user.id)

    with pytest.raises(HTTPException) as error:
        CartService.add_item(
            db,
            cart,
            CartItemCreate(
                product_id=product.id,
                quantity=1,
            ),
        )

    assert error.value.status_code == 400
    assert error.value.detail == "Product is out of stock."


def test_flag_overrides_a_positive_quantity(
    db: Session,
):
    """
    An operator switching a product off must take it off
    sale even if the count says there are units left.
    """

    user = create_test_user(db)

    product = create_test_product(
        db,
        in_stock=False,
        stock_quantity=10,
    )

    cart = CartService.get_or_create_cart(db, user.id)

    with pytest.raises(HTTPException) as error:
        CartService.add_item(
            db,
            cart,
            CartItemCreate(
                product_id=product.id,
                quantity=1,
            ),
        )

    assert error.value.detail == "Product is out of stock."


# ==========================================
# Counted Products Are Enforced
# ==========================================

def test_cannot_add_more_than_stock(
    db: Session,
):
    user = create_test_user(db)

    product = create_test_product(
        db,
        stock_quantity=3,
    )

    cart = CartService.get_or_create_cart(db, user.id)

    with pytest.raises(HTTPException) as error:
        CartService.add_item(
            db,
            cart,
            CartItemCreate(
                product_id=product.id,
                quantity=4,
            ),
        )

    assert error.value.status_code == 400
    assert "Only 3 left in stock" in error.value.detail


def test_repeated_adds_cannot_exceed_stock(
    db: Session,
):
    """
    The limit applies to what the cart ends up holding, not
    to each request, or it could be walked past one unit at
    a time.
    """

    user = create_test_user(db)

    product = create_test_product(
        db,
        stock_quantity=3,
    )

    cart = CartService.get_or_create_cart(db, user.id)

    CartService.add_item(
        db,
        cart,
        CartItemCreate(
            product_id=product.id,
            quantity=2,
        ),
    )

    with pytest.raises(HTTPException) as error:
        CartService.add_item(
            db,
            cart,
            CartItemCreate(
                product_id=product.id,
                quantity=2,
            ),
        )

    assert "Only 3 left in stock" in error.value.detail


def test_cannot_update_item_beyond_stock(
    db: Session,
):
    user = create_test_user(db)

    product = create_test_product(
        db,
        stock_quantity=2,
    )

    cart = CartService.get_or_create_cart(db, user.id)

    item = CartService.add_item(
        db,
        cart,
        CartItemCreate(
            product_id=product.id,
            quantity=1,
        ),
    )

    with pytest.raises(HTTPException) as error:
        CartService.update_item(
            db,
            cart,
            item.id,
            CartItemUpdate(quantity=5),
        )

    assert "Only 2 left in stock" in error.value.detail


def test_sync_cannot_exceed_stock(
    db: Session,
):
    user = create_test_user(db)

    product = create_test_product(
        db,
        stock_quantity=1,
    )

    cart = CartService.get_or_create_cart(db, user.id)

    with pytest.raises(HTTPException) as error:
        CartService.sync_cart(
            db,
            cart,
            [
                CartItemCreate(
                    product_id=product.id,
                    quantity=2,
                ),
            ],
        )

    assert error.value.status_code == 400
    assert "Insufficient stock" in error.value.detail


def test_order_creation_rechecks_stock(
    db: Session,
):
    """
    Stock can fall between filling the cart and checking
    out, so the cart's own check is not enough.
    """

    user = create_test_user(db)

    product = create_test_product(
        db,
        stock_quantity=5,
    )

    create_cart_with(db, user, product, 4)

    product.stock_quantity = 2

    db.commit()

    with pytest.raises(HTTPException) as error:
        OrderService.create_order_from_cart(db, user.id)

    assert error.value.status_code == 400
    assert "Only 2 left in stock" in error.value.detail


# ==========================================
# Stock Leaves The Shelf On Payment
# ==========================================

def test_settlement_decrements_stock(
    db: Session,
):
    user = create_test_user(db)

    product = create_test_product(
        db,
        stock_quantity=10,
    )

    create_cart_with(db, user, product, 3)

    order = OrderService.create_order_from_cart(
        db,
        user.id,
    )

    db.refresh(product)

    # Nothing has been paid yet, so nothing has moved.
    assert product.stock_quantity == 10

    settle(db, user, order)

    db.refresh(product)

    assert product.stock_quantity == 7
    assert product.in_stock is True


def test_last_unit_takes_the_product_off_sale(
    db: Session,
):
    user = create_test_user(db)

    product = create_test_product(
        db,
        stock_quantity=2,
    )

    create_cart_with(db, user, product, 2)

    order = OrderService.create_order_from_cart(
        db,
        user.id,
    )

    settle(db, user, order)

    db.refresh(product)

    assert product.stock_quantity == 0
    assert product.in_stock is False


def test_failed_payment_does_not_decrement_stock(
    db: Session,
):
    user = create_test_user(db)

    product = create_test_product(
        db,
        stock_quantity=4,
    )

    create_cart_with(db, user, product, 2)

    order = OrderService.create_order_from_cart(
        db,
        user.id,
    )

    settle(db, user, order, status="failed")

    db.refresh(product)

    assert product.stock_quantity == 4


def test_replayed_settlement_does_not_decrement_twice(
    db: Session,
):
    """
    Paystack retries. Stock must move once per order, not
    once per delivery attempt.
    """

    user = create_test_user(db)

    product = create_test_product(
        db,
        stock_quantity=10,
    )

    create_cart_with(db, user, product, 3)

    order = OrderService.create_order_from_cart(
        db,
        user.id,
    )

    payment = settle(db, user, order)

    PaymentService.settle_payment(
        db,
        payment,
        {
            "reference": payment.reference,
            "amount": int(payment.amount * 100),
            "currency": "NGN",
            "status": "success",
            "channel": "card",
            "id": 555_002,
        },
    )

    db.refresh(product)

    assert product.stock_quantity == 7


def test_oversell_is_clamped_and_the_order_is_honoured(
    db: Session,
):
    """
    Two customers can pass the checkout check and pay for
    the same last unit. Once money has moved, refusing the
    order would leave a customer charged for nothing, so the
    order stands and the shortfall is logged instead.
    """

    user = create_test_user(db)

    product = create_test_product(
        db,
        stock_quantity=5,
    )

    create_cart_with(db, user, product, 5)

    order = OrderService.create_order_from_cart(
        db,
        user.id,
    )

    # Somebody else's payment landed first.
    product.stock_quantity = 2

    db.commit()

    settle(db, user, order)

    db.refresh(product)
    db.refresh(order)

    assert product.stock_quantity == 0
    assert product.in_stock is False
    assert order.status == "paid"
