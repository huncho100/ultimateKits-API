from decimal import Decimal
import uuid

from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.models.order import Order
from app.models.product import Product
from app.models.user import User
from app.utils.security import create_access_token


# ==========================================
# Test Helpers
# ==========================================

def create_test_user(
    db,
    *,
    role: str = "customer",
) -> User:
    """
    Create a user for order route tests.
    """

    user = User(
        first_name="Order",
        last_name="Route Test",
        email=(
            f"order_route_{uuid.uuid4().hex[:10]}"
            "@example.com"
        ),
        password_hash="test-password-hash",
        role=role,
        is_active=True,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def auth_headers(
    user: User,
) -> dict:
    """
    Generate authentication headers for
    a test user.
    """

    token = create_access_token(
        {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role,
        }
    )

    return {
        "Authorization": f"Bearer {token}",
    }


def create_test_product(
    db,
    *,
    name: str = "Order Route Jersey",
    price: Decimal = Decimal("89.99"),
    in_stock: bool = True,
) -> Product:
    """
    Create a product for route tests.
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
    db,
    user: User,
) -> Cart:
    """
    Create a cart for a test user.
    """

    cart = Cart(
        user_id=user.id,
    )

    db.add(cart)
    db.commit()
    db.refresh(cart)

    return cart


def add_cart_item(
    db,
    cart: Cart,
    product: Product,
    *,
    quantity: int = 1,
) -> CartItem:
    """
    Add an item directly to a test cart.
    """

    item = CartItem(
        cart_id=cart.id,
        product_id=product.id,
        quantity=quantity,
    )

    db.add(item)
    db.commit()
    db.refresh(item)

    return item


# ==========================================
# Create Order
# ==========================================

def test_create_order_from_cart(
    client,
    db,
):
    """
    Authenticated users should be able to
    create an order from their cart.
    """

    user = create_test_user(db)

    product = create_test_product(
        db,
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
        quantity=2,
    )

    response = client.post(
        "/orders",
        headers=auth_headers(user),
    )

    assert response.status_code == 201

    data = response.json()

    assert data["id"] is not None
    assert data["user_id"] == user.id
    assert data["status"] == "pending"

    assert Decimal(
        data["total_amount"]
    ) == Decimal("100.00")

    assert len(data["items"]) == 1

    item = data["items"][0]

    assert item["product_id"] == product.id
    assert item["quantity"] == 2

    assert Decimal(
        item["unit_price"]
    ) == Decimal("50.00")

    assert Decimal(
        item["subtotal"]
    ) == Decimal("100.00")

    print(
        "✓ Create order route test passed"
    )


# ==========================================
# Checkout Requires Authentication
# ==========================================

def test_create_order_requires_authentication(
    client,
):
    """
    Checkout should require authentication.
    """

    response = client.post(
        "/orders",
    )

    assert response.status_code == 401

    print(
        "✓ Create order authentication "
        "test passed"
    )


# ==========================================
# Empty Cart
# ==========================================

def test_create_order_from_empty_cart(
    client,
    db,
):
    """
    Checkout with an empty cart should fail.
    """

    user = create_test_user(db)

    create_test_cart(
        db,
        user,
    )

    response = client.post(
        "/orders",
        headers=auth_headers(user),
    )

    assert response.status_code == 400

    data = response.json()

    assert data["detail"] == (
        "Cannot create an order from an empty cart."
    )

    print(
        "✓ Empty cart checkout route "
        "test passed"
    )


# ==========================================
# Get User Orders
# ==========================================

def test_get_user_orders(
    client,
    db,
):
    """
    Users should retrieve their own orders.
    """

    user = create_test_user(db)

    order = Order(
        user_id=user.id,
        status="pending",
        total_amount=Decimal("150.00"),
    )

    db.add(order)
    db.commit()
    db.refresh(order)

    response = client.get(
        "/orders",
        headers=auth_headers(user),
    )

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)
    assert len(data) == 1

    assert data[0]["id"] == order.id
    assert data[0]["user_id"] == user.id

    assert Decimal(
        data[0]["total_amount"]
    ) == Decimal("150.00")

    print(
        "✓ Get user orders route test "
        "passed"
    )


# ==========================================
# Get Orders Requires Authentication
# ==========================================

def test_get_orders_requires_authentication(
    client,
):
    """
    Order history should require authentication.
    """

    response = client.get(
        "/orders",
    )

    assert response.status_code == 401

    print(
        "✓ Order history authentication "
        "test passed"
    )


# ==========================================
# Get Order By ID
# ==========================================

def test_get_order_by_id(
    client,
    db,
):
    """
    A user should retrieve their own order.
    """

    user = create_test_user(db)

    order = Order(
        user_id=user.id,
        status="pending",
        total_amount=Decimal("200.00"),
    )

    db.add(order)
    db.commit()
    db.refresh(order)

    response = client.get(
        f"/orders/{order.id}",
        headers=auth_headers(user),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == order.id
    assert data["user_id"] == user.id
    assert data["status"] == "pending"

    assert Decimal(
        data["total_amount"]
    ) == Decimal("200.00")

    print(
        "✓ Get order by ID route test "
        "passed"
    )


# ==========================================
# Get Nonexistent Order
# ==========================================

def test_get_nonexistent_order(
    client,
    db,
):
    """
    A nonexistent order should return 404.
    """

    user = create_test_user(db)

    response = client.get(
        "/orders/999999",
        headers=auth_headers(user),
    )

    assert response.status_code == 404

    data = response.json()

    assert data["detail"] == (
        "Order not found."
    )

    print(
        "✓ Get nonexistent order route "
        "test passed"
    )


# ==========================================
# User Cannot Access Another User's Order
# ==========================================

def test_user_cannot_access_another_users_order(
    client,
    db,
):
    """
    Users must not be able to retrieve
    another user's order.
    """

    user_one = create_test_user(db)

    user_two = create_test_user(db)

    order = Order(
        user_id=user_one.id,
        status="pending",
        total_amount=Decimal("100.00"),
    )

    db.add(order)
    db.commit()
    db.refresh(order)

    response = client.get(
        f"/orders/{order.id}",
        headers=auth_headers(user_two),
    )

    assert response.status_code == 403

    data = response.json()

    assert data["detail"] == (
        "You do not have access to this order."
    )

    print(
        "✓ Order ownership protection "
        "test passed"
    )


# ==========================================
# User Orders Are Isolated
# ==========================================

def test_user_orders_are_isolated(
    client,
    db,
):
    """
    Users should only see their own
    order history.
    """

    user_one = create_test_user(db)

    user_two = create_test_user(db)

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
    db.add(order_two)

    db.commit()

    response = client.get(
        "/orders",
        headers=auth_headers(user_one),
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1

    assert data[0]["id"] == order_one.id

    assert data[0]["user_id"] == user_one.id

    print(
        "✓ User order isolation test passed"
    )


# ==========================================
# Order By ID Requires Authentication
# ==========================================

def test_get_order_requires_authentication(
    client,
    db,
):
    """
    Retrieving an order by ID should require
    authentication.
    """

    user = create_test_user(db)

    order = Order(
        user_id=user.id,
        status="pending",
        total_amount=Decimal("100.00"),
    )

    db.add(order)
    db.commit()
    db.refresh(order)

    response = client.get(
        f"/orders/{order.id}",
    )

    assert response.status_code == 401

    print(
        "✓ Order by ID authentication "
        "test passed"
    )