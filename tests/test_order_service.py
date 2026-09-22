from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.models.order import Order
from app.models.product import Product
from app.models.user import User
from app.services.order_service import OrderService


# ==========================================
# Test Helpers
# ==========================================

def create_test_user(
    db: Session,
    email: str = "order-test@example.com",
) -> User:
    """
    Create a user for order service tests.
    """

    user = User(
        first_name="Order",
        last_name="Test",
        email=email,
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
    name: str = "Test Jersey",
    price: Decimal = Decimal("89.99"),
    in_stock: bool = True,
) -> Product:
    """
    Create a product for order service tests.
    """

    product = Product(
        name=name,
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
    )

    db.add(product)
    db.commit()
    db.refresh(product)

    return product


def create_test_cart(
    db: Session,
    user: User,
) -> Cart:
    """
    Create a cart for a user.
    """

    cart = Cart(
        user_id=user.id,
    )

    db.add(cart)
    db.commit()
    db.refresh(cart)

    return cart


def add_cart_item(
    db: Session,
    cart: Cart,
    product: Product,
    quantity: int,
) -> CartItem:
    """
    Add a product directly to a test cart.
    """

    cart_item = CartItem(
        cart_id=cart.id,
        product_id=product.id,
        quantity=quantity,
    )

    db.add(cart_item)
    db.commit()
    db.refresh(cart_item)

    return cart_item


# ==========================================
# Create Order From Cart
# ==========================================

def test_create_order_from_cart(
    db: Session,
):
    """
    A populated cart should successfully
    create an order.
    """

    user = create_test_user(db)
    product = create_test_product(db)

    cart = create_test_cart(
        db,
        user,
    )

    add_cart_item(
        db,
        cart,
        product,
        quantity=2,
    )

    order = OrderService.create_order_from_cart(
        db,
        user.id,
    )

    assert order.id is not None
    assert order.user_id == user.id
    assert order.status == "pending"

    assert order.total_amount == Decimal(
        "179.98"
    )

    assert len(order.items) == 1

    print(
        "✓ Create order from cart service "
        "test passed"
    )


# ==========================================
# Order Item Creation
# ==========================================

def test_order_items_created_from_cart(
    db: Session,
):
    """
    Cart items should be converted into
    order items.
    """

    user = create_test_user(
        db,
        email="items@example.com",
    )

    product = create_test_product(
        db,
        name="Items Jersey",
        price=Decimal("50.00"),
    )

    cart = create_test_cart(
        db,
        user,
    )

    add_cart_item(
        db,
        cart,
        product,
        quantity=3,
    )

    order = OrderService.create_order_from_cart(
        db,
        user.id,
    )

    assert len(order.items) == 1

    order_item = order.items[0]

    assert order_item.product_id == product.id
    assert order_item.quantity == 3
    assert order_item.unit_price == Decimal(
        "50.00"
    )
    assert order_item.subtotal == Decimal(
        "150.00"
    )

    print(
        "✓ Order items created from cart "
        "test passed"
    )


# ==========================================
# Multiple Cart Items
# ==========================================

def test_create_order_with_multiple_items(
    db: Session,
):
    """
    Multiple cart items should create
    multiple order items and the correct total.
    """

    user = create_test_user(
        db,
        email="multiple@example.com",
    )

    product_one = create_test_product(
        db,
        name="First Jersey",
        price=Decimal("50.00"),
    )

    product_two = create_test_product(
        db,
        name="Second Jersey",
        price=Decimal("30.00"),
    )

    cart = create_test_cart(
        db,
        user,
    )

    add_cart_item(
        db,
        cart,
        product_one,
        quantity=2,
    )

    add_cart_item(
        db,
        cart,
        product_two,
        quantity=3,
    )

    order = OrderService.create_order_from_cart(
        db,
        user.id,
    )

    assert len(order.items) == 2

    assert order.total_amount == Decimal(
        "190.00"
    )

    print(
        "✓ Multiple order items test passed"
    )


# ==========================================
# Price Snapshot
# ==========================================

def test_order_preserves_product_price_snapshot(
    db: Session,
):
    """
    The order item should preserve the product
    price at the moment of checkout.
    """

    user = create_test_user(
        db,
        email="snapshot@example.com",
    )

    product = create_test_product(
        db,
        name="Snapshot Jersey",
        price=Decimal("80.00"),
    )

    cart = create_test_cart(
        db,
        user,
    )

    add_cart_item(
        db,
        cart,
        product,
        quantity=2,
    )

    order = OrderService.create_order_from_cart(
        db,
        user.id,
    )

    order_item = order.items[0]

    # Change the current product price after
    # checkout.
    product.price = Decimal("120.00")

    db.commit()
    db.refresh(product)
    db.refresh(order_item)

    assert order_item.unit_price == Decimal(
        "80.00"
    )

    assert order_item.subtotal == Decimal(
        "160.00"
    )

    print(
        "✓ Product price snapshot test passed"
    )


# ==========================================
# Cart Survives Checkout
# ==========================================

def test_cart_survives_order_creation(
    db: Session,
):
    """
    Placing an order must not empty the cart.

    The order is only a request to pay. If the cart were
    cleared here, a customer whose card was declined would
    come back to an empty basket and have to rebuild it from
    memory. The cart is emptied when the payment succeeds.
    """

    user = create_test_user(
        db,
        email="clear@example.com",
    )

    product = create_test_product(
        db,
        name="Clear Cart Jersey",
    )

    cart = create_test_cart(
        db,
        user,
    )

    add_cart_item(
        db,
        cart,
        product,
        quantity=1,
    )

    OrderService.create_order_from_cart(
        db,
        user.id,
    )

    db.refresh(cart)

    assert len(cart.items) == 1
    assert cart.items[0].product_id == product.id

    print(
        "✓ Cart survives checkout test passed"
    )


# ==========================================
# Repeated Checkout
# ==========================================

def test_repeated_checkout_reuses_pending_order(
    db: Session,
):
    """
    A double-submitted checkout must not leave the customer
    with two orders for the same basket.
    """

    user = create_test_user(
        db,
        email="repeat-checkout@example.com",
    )

    product = create_test_product(
        db,
        name="Repeat Checkout Jersey",
    )

    cart = create_test_cart(
        db,
        user,
    )

    add_cart_item(
        db,
        cart,
        product,
        quantity=2,
    )

    first = OrderService.create_order_from_cart(
        db,
        user.id,
    )

    second = OrderService.create_order_from_cart(
        db,
        user.id,
    )

    assert second.id == first.id

    orders = (
        db.query(Order)
        .filter(Order.user_id == user.id)
        .all()
    )

    assert len(orders) == 1

    print(
        "✓ Repeated checkout test passed"
    )


# ==========================================
# Changed Cart Produces A New Order
# ==========================================

def test_changed_cart_creates_a_new_order(
    db: Session,
):
    """
    Reuse is keyed on what is actually being bought, so
    adding to the basket still produces a distinct order.
    """

    user = create_test_user(
        db,
        email="changed-cart@example.com",
    )

    product = create_test_product(
        db,
        name="Changed Cart Jersey",
    )

    cart = create_test_cart(
        db,
        user,
    )

    cart_item = add_cart_item(
        db,
        cart,
        product,
        quantity=1,
    )

    first = OrderService.create_order_from_cart(
        db,
        user.id,
    )

    cart_item.quantity = 3

    db.commit()
    db.refresh(cart)

    second = OrderService.create_order_from_cart(
        db,
        user.id,
    )

    assert second.id != first.id
    assert second.items[0].quantity == 3

    print(
        "✓ Changed cart test passed"
    )


# ==========================================
# Empty Cart
# ==========================================

def test_create_order_from_empty_cart(
    db: Session,
):
    """
    Creating an order from an empty cart
    should fail.
    """

    user = create_test_user(
        db,
        email="empty@example.com",
    )

    create_test_cart(
        db,
        user,
    )

    with pytest.raises(
        HTTPException,
    ) as error:

        OrderService.create_order_from_cart(
            db,
            user.id,
        )

    assert error.value.status_code == 400

    assert error.value.detail == (
        "Cannot create an order from an empty cart."
    )

    print(
        "✓ Empty cart checkout test passed"
    )


# ==========================================
# No Cart
# ==========================================

def test_create_order_without_cart(
    db: Session,
):
    """
    A user without a cart should not be able
    to create an order.
    """

    user = create_test_user(
        db,
        email="no-cart@example.com",
    )

    with pytest.raises(
        HTTPException,
    ) as error:

        OrderService.create_order_from_cart(
            db,
            user.id,
        )

    assert error.value.status_code == 400

    assert error.value.detail == (
        "Cannot create an order from an empty cart."
    )

    print(
        "✓ No cart checkout test passed"
    )


# ==========================================
# Out Of Stock Product
# ==========================================

def test_create_order_with_out_of_stock_product(
    db: Session,
):
    """
    Checkout should fail when a product
    in the cart is out of stock.
    """

    user = create_test_user(
        db,
        email="out-of-stock@example.com",
    )

    product = create_test_product(
        db,
        name="Out Of Stock Jersey",
        in_stock=False,
    )

    cart = create_test_cart(
        db,
        user,
    )

    add_cart_item(
        db,
        cart,
        product,
        quantity=1,
    )

    with pytest.raises(
        HTTPException,
    ) as error:

        OrderService.create_order_from_cart(
            db,
            user.id,
        )

    assert error.value.status_code == 400

    assert error.value.detail == (
        "Product is out of stock."
    )

    print(
        "✓ Out of stock checkout test passed"
    )


# ==========================================
# Get User Orders
# ==========================================

def test_get_user_orders(
    db: Session,
):
    """
    A user should only receive their own orders.
    """

    user_one = create_test_user(
        db,
        email="user-one@example.com",
    )

    user_two = create_test_user(
        db,
        email="user-two@example.com",
    )

    order_one = Order(
        user_id=user_one.id,
        status="pending",
        total_amount=Decimal("50.00"),
    )

    order_two = Order(
        user_id=user_two.id,
        status="pending",
        total_amount=Decimal("75.00"),
    )

    db.add(order_one)

    # Fix the second order user assignment before
    # persisting it.
    order_two.user_id = user_two.id

    db.add(order_two)

    db.commit()

    orders = OrderService.get_user_orders(
        db,
        user_one.id,
    )

    assert len(orders) == 1
    assert orders[0].id == order_one.id

    print(
        "✓ Get user orders isolation test passed"
    )


# ==========================================
# Get Order By ID
# ==========================================

def test_get_order_by_id(
    db: Session,
):
    """
    An existing order should be retrieved
    by its ID.
    """

    user = create_test_user(
        db,
        email="get-order@example.com",
    )

    order = Order(
        user_id=user.id,
        status="pending",
        total_amount=Decimal("100.00"),
    )

    db.add(order)
    db.commit()
    db.refresh(order)

    result = OrderService.get_order_by_id(
        db,
        order.id,
    )

    assert result is not None
    assert result.id == order.id
    assert result.user_id == user.id

    print(
        "✓ Get order by ID test passed"
    )


# ==========================================
# Get Nonexistent Order
# ==========================================

def test_get_nonexistent_order(
    db: Session,
):
    """
    A nonexistent order should return None.
    """

    result = OrderService.get_order_by_id(
        db,
        999999,
    )

    assert result is None

    print(
        "✓ Get nonexistent order test passed"
    )