from decimal import Decimal
import uuid

from app.models.cart import Cart
from app.models.cart_item import CartItem
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
    is_active: bool = True,
):
    """
    Create a test user for route authentication.
    """

    user = User(
        first_name="Cart",
        last_name="Route",
        email=(
            f"cart_route_{uuid.uuid4().hex[:8]}"
            "@example.com"
        ),
        password_hash="test-password-hash",
        role=role,
        is_active=is_active,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def create_test_product(
    db,
    *,
    name: str = "Test Cart Jersey",
    price: Decimal = Decimal("89.99"),
    in_stock: bool = True,
):
    """
    Create a test product.
    """

    product = Product(
        name=name,
        sport="Football",
        category="Jerseys",
        team="Test FC",
        league="Test League",
        brand="Test Brand",
        price=price,
        old_price=Decimal("99.99"),
        rating=4.5,
        image="/images/test.jpg",
        is_featured=False,
        is_new=True,
        is_best_seller=False,
        in_stock=in_stock,
    )

    db.add(product)
    db.commit()
    db.refresh(product)

    return product


def auth_headers(user):
    """
    Create Authorization headers for a test user.
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


# ==========================================
# Get Cart
# ==========================================

def test_get_cart(
    client,
    db,
):
    user = create_test_user(db)

    response = client.get(
        "/cart",
        headers=auth_headers(user),
    )

    assert response.status_code == 200

    data = response.json()

    assert "id" in data
    assert data["user_id"] == user.id

    assert "items" in data
    assert isinstance(data["items"], list)

    print("✓ Get cart route test passed")


# ==========================================
# Get Cart Requires Authentication
# ==========================================

def test_get_cart_requires_authentication(
    client,
):
    response = client.get("/cart")

    assert response.status_code == 401

    print("✓ Get cart authentication test passed")


# ==========================================
# Add Item
# ==========================================

def test_add_cart_item(
    client,
    db,
):
    user = create_test_user(db)
    product = create_test_product(db)

    response = client.post(
        "/cart/items",
        json={
            "product_id": product.id,
            "quantity": 2,
        },
        headers=auth_headers(user),
    )

    assert response.status_code == 201

    data = response.json()

    assert data["product_id"] == product.id
    assert data["quantity"] == 2

    print("✓ Add cart item route test passed")


# ==========================================
# Add Existing Item
# ==========================================

def test_add_existing_cart_item(
    client,
    db,
):
    user = create_test_user(db)
    product = create_test_product(db)

    headers = auth_headers(user)

    first_response = client.post(
        "/cart/items",
        json={
            "product_id": product.id,
            "quantity": 2,
        },
        headers=headers,
    )

    assert first_response.status_code == 201

    first_item = first_response.json()

    second_response = client.post(
        "/cart/items",
        json={
            "product_id": product.id,
            "quantity": 3,
        },
        headers=headers,
    )

    assert second_response.status_code == 201

    second_item = second_response.json()

    assert second_item["id"] == first_item["id"]
    assert second_item["quantity"] == 5

    print("✓ Add existing cart item route test passed")


# ==========================================
# Add Nonexistent Product
# ==========================================

def test_add_nonexistent_product(
    client,
    db,
):
    user = create_test_user(db)

    response = client.post(
        "/cart/items",
        json={
            "product_id": 999999,
            "quantity": 1,
        },
        headers=auth_headers(user),
    )

    assert response.status_code == 404

    data = response.json()

    assert data["detail"] == "Product not found."

    print("✓ Add nonexistent product route test passed")


# ==========================================
# Add Out Of Stock Product
# ==========================================

def test_add_out_of_stock_product(
    client,
    db,
):
    user = create_test_user(db)

    product = create_test_product(
        db,
        in_stock=False,
    )

    response = client.post(
        "/cart/items",
        json={
            "product_id": product.id,
            "quantity": 1,
        },
        headers=auth_headers(user),
    )

    assert response.status_code == 400

    data = response.json()

    assert data["detail"] == "Product is out of stock."

    print("✓ Out of stock cart route test passed")


# ==========================================
# Update Cart Item
# ==========================================

def test_update_cart_item(
    client,
    db,
):
    user = create_test_user(db)
    product = create_test_product(db)

    headers = auth_headers(user)

    create_response = client.post(
        "/cart/items",
        json={
            "product_id": product.id,
            "quantity": 2,
        },
        headers=headers,
    )

    assert create_response.status_code == 201

    item_id = create_response.json()["id"]

    response = client.patch(
        f"/cart/items/{item_id}",
        json={
            "quantity": 5,
        },
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == item_id
    assert data["quantity"] == 5

    print("✓ Update cart item route test passed")


# ==========================================
# Update Nonexistent Cart Item
# ==========================================

def test_update_nonexistent_cart_item(
    client,
    db,
):
    user = create_test_user(db)

    response = client.patch(
        "/cart/items/999999",
        json={
            "quantity": 5,
        },
        headers=auth_headers(user),
    )

    assert response.status_code == 404

    data = response.json()

    assert data["detail"] == "Cart item not found."

    print("✓ Update nonexistent cart item route test passed")


# ==========================================
# Remove Cart Item
# ==========================================

def test_remove_cart_item(
    client,
    db,
):
    user = create_test_user(db)
    product = create_test_product(db)

    headers = auth_headers(user)

    create_response = client.post(
        "/cart/items",
        json={
            "product_id": product.id,
            "quantity": 2,
        },
        headers=headers,
    )

    assert create_response.status_code == 201

    item_id = create_response.json()["id"]

    response = client.delete(
        f"/cart/items/{item_id}",
        headers=headers,
    )

    assert response.status_code == 204
    assert response.content == b""

    get_cart_response = client.get(
        "/cart",
        headers=headers,
    )

    assert get_cart_response.status_code == 200

    items = get_cart_response.json()["items"]

    assert all(
        item["id"] != item_id
        for item in items
    )

    print("✓ Remove cart item route test passed")


# ==========================================
# Remove Nonexistent Cart Item
# ==========================================

def test_remove_nonexistent_cart_item(
    client,
    db,
):
    user = create_test_user(db)

    response = client.delete(
        "/cart/items/999999",
        headers=auth_headers(user),
    )

    assert response.status_code == 404

    data = response.json()

    assert data["detail"] == "Cart item not found."

    print("✓ Remove nonexistent cart item route test passed")


# ==========================================
# Clear Cart
# ==========================================

def test_clear_cart(
    client,
    db,
):
    user = create_test_user(db)

    product_one = create_test_product(
        db,
        name="Cart Jersey One",
    )

    product_two = create_test_product(
        db,
        name="Cart Jersey Two",
    )

    headers = auth_headers(user)

    client.post(
        "/cart/items",
        json={
            "product_id": product_one.id,
            "quantity": 2,
        },
        headers=headers,
    )

    client.post(
        "/cart/items",
        json={
            "product_id": product_two.id,
            "quantity": 3,
        },
        headers=headers,
    )

    response = client.delete(
        "/cart",
        headers=headers,
    )

    assert response.status_code == 204
    assert response.content == b""

    get_cart_response = client.get(
        "/cart",
        headers=headers,
    )

    assert get_cart_response.status_code == 200

    data = get_cart_response.json()

    assert data["items"] == []

    print("✓ Clear cart route test passed")


# ==========================================
# Clear Empty Cart
# ==========================================

def test_clear_empty_cart(
    client,
    db,
):
    user = create_test_user(db)

    response = client.delete(
        "/cart",
        headers=auth_headers(user),
    )

    assert response.status_code == 204
    assert response.content == b""

    print("✓ Clear empty cart route test passed")


# ==========================================
# Cart Isolation
# ==========================================

def test_cart_isolation_between_users(
    client,
    db,
):
    user_one = create_test_user(db)
    user_two = create_test_user(db)

    product = create_test_product(db)

    user_one_headers = auth_headers(user_one)
    user_two_headers = auth_headers(user_two)

    add_response = client.post(
        "/cart/items",
        json={
            "product_id": product.id,
            "quantity": 3,
        },
        headers=user_one_headers,
    )

    assert add_response.status_code == 201

    item_id = add_response.json()["id"]

    user_two_cart = client.get(
        "/cart",
        headers=user_two_headers,
    )

    assert user_two_cart.status_code == 200

    assert user_two_cart.json()["items"] == []

    # User two cannot modify user one's cart item.
    update_response = client.patch(
        f"/cart/items/{item_id}",
        json={
            "quantity": 10,
        },
        headers=user_two_headers,
    )

    assert update_response.status_code == 404
    assert (
        update_response.json()["detail"]
        == "Cart item not found."
    )

    # User two cannot delete user one's cart item.
    delete_response = client.delete(
        f"/cart/items/{item_id}",
        headers=user_two_headers,
    )

    assert delete_response.status_code == 404
    assert (
        delete_response.json()["detail"]
        == "Cart item not found."
    )

    print("✓ Cart isolation route test passed")


# ==========================================
# Cart Requires Authentication
# ==========================================

def test_add_cart_item_requires_authentication(
    client,
    db,
):
    product = create_test_product(db)

    response = client.post(
        "/cart/items",
        json={
            "product_id": product.id,
            "quantity": 1,
        },
    )

    assert response.status_code == 401

    print("✓ Add cart item authentication test passed")


def test_update_cart_item_requires_authentication(
    client,
):
    response = client.patch(
        "/cart/items/1",
        json={
            "quantity": 2,
        },
    )

    assert response.status_code == 401

    print("✓ Update cart item authentication test passed")


def test_remove_cart_item_requires_authentication(
    client,
):
    response = client.delete(
        "/cart/items/1",
    )

    assert response.status_code == 401

    print("✓ Remove cart item authentication test passed")


def test_clear_cart_requires_authentication(
    client,
):
    response = client.delete("/cart")

    assert response.status_code == 401

    print("✓ Clear cart authentication test passed")


# ==========================================
# Add Cart Item With Invalid Quantity
# ==========================================

def test_add_cart_item_invalid_quantity(
    client,
    db,
):
    user = create_test_user(db)
    product = create_test_product(db)

    headers = auth_headers(user)

    zero_response = client.post(
        "/cart/items",
        json={
            "product_id": product.id,
            "quantity": 0,
        },
        headers=headers,
    )

    assert zero_response.status_code == 422

    negative_response = client.post(
        "/cart/items",
        json={
            "product_id": product.id,
            "quantity": -1,
        },
        headers=headers,
    )

    assert negative_response.status_code == 422

    print(
        "✓ Invalid cart item quantity "
        "validation test passed"
    )


# ==========================================
# Update Cart Item With Invalid Quantity
# ==========================================

def test_update_cart_item_invalid_quantity(
    client,
    db,
):
    user = create_test_user(db)
    product = create_test_product(db)

    headers = auth_headers(user)

    create_response = client.post(
        "/cart/items",
        json={
            "product_id": product.id,
            "quantity": 2,
        },
        headers=headers,
    )

    assert create_response.status_code == 201

    item_id = create_response.json()["id"]

    zero_response = client.patch(
        f"/cart/items/{item_id}",
        json={
            "quantity": 0,
        },
        headers=headers,
    )

    assert zero_response.status_code == 422

    negative_response = client.patch(
        f"/cart/items/{item_id}",
        json={
            "quantity": -5,
        },
        headers=headers,
    )

    assert negative_response.status_code == 422

    print(
        "✓ Invalid cart update quantity "
        "validation test passed"
    )