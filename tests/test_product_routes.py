import uuid
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.user import User
from app.utils.security import create_access_token


# ==========================================
# Test Product Data
# ==========================================

PRODUCT_DATA = {
    "name": "Manchester United Home Jersey",
    "sport": "Football",
    "category": "Jerseys",
    "team": "Manchester United",
    "league": "Premier League",
    "brand": "Adidas",
    "price": "89.99",
    "old_price": "109.99",
    "rating": 4.5,
    "image": "/images/manchester-united-home.jpg",
    "is_featured": True,
    "is_new": True,
    "is_best_seller": False,
    "in_stock": True,
}


# ==========================================
# Authentication Helpers
# ==========================================

def create_user_headers(
    db: Session,
    *,
    role: str = "customer",
) -> dict:
    """
    Create an authenticated user and return
    Authorization headers.
    """

    user = User(
        first_name="Product",
        last_name="User",
        email=(
            f"product_{role}_"
            f"{uuid.uuid4().hex[:8]}"
            "@example.com"
        ),
        password_hash="test-password-hash",
        role=role,
        is_active=True,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

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


def create_admin_headers(
    db: Session,
) -> dict:
    """
    Create an authenticated administrator and return
    Authorization headers.
    """

    return create_user_headers(
        db,
        role="admin",
    )


def create_customer_headers(
    db: Session,
) -> dict:
    """
    Create an authenticated customer and return
    Authorization headers.
    """

    return create_user_headers(
        db,
        role="customer",
    )


# ==========================================
# Product Helper
# ==========================================

def create_test_product(
    db: Session,
) -> Product:
    """
    Create a product directly in the database.

    Used when testing public read endpoints or
    authorization without depending on the create
    product route.
    """

    product = Product(
        name=PRODUCT_DATA["name"],
        sport=PRODUCT_DATA["sport"],
        category=PRODUCT_DATA["category"],
        team=PRODUCT_DATA["team"],
        league=PRODUCT_DATA["league"],
        brand=PRODUCT_DATA["brand"],
        price=Decimal(PRODUCT_DATA["price"]),
        old_price=Decimal(PRODUCT_DATA["old_price"]),
        rating=PRODUCT_DATA["rating"],
        image=PRODUCT_DATA["image"],
        is_featured=PRODUCT_DATA["is_featured"],
        is_new=PRODUCT_DATA["is_new"],
        is_best_seller=PRODUCT_DATA[
            "is_best_seller"
        ],
        in_stock=PRODUCT_DATA["in_stock"],
    )

    db.add(product)
    db.commit()
    db.refresh(product)

    return product


# ==========================================
# Create Product
# ==========================================

def test_create_product(
    client,
    db,
):
    headers = create_admin_headers(db)

    response = client.post(
        "/products",
        json=PRODUCT_DATA,
        headers=headers,
    )

    assert response.status_code == 201

    data = response.json()

    assert "id" in data
    assert data["name"] == PRODUCT_DATA["name"]
    assert data["sport"] == PRODUCT_DATA["sport"]
    assert data["category"] == PRODUCT_DATA["category"]
    assert data["team"] == PRODUCT_DATA["team"]
    assert data["league"] == PRODUCT_DATA["league"]
    assert data["brand"] == PRODUCT_DATA["brand"]
    assert Decimal(data["price"]) == Decimal(
        "89.99"
    )
    assert Decimal(data["old_price"]) == Decimal(
        "109.99"
    )
    assert data["rating"] == 4.5
    assert data["is_featured"] is True
    assert data["is_new"] is True
    assert data["is_best_seller"] is False
    assert data["in_stock"] is True

    print(
        "✓ Admin create product route test passed"
    )


# ==========================================
# Create Product Requires Authentication
# ==========================================

def test_create_product_requires_authentication(
    client,
):
    response = client.post(
        "/products",
        json=PRODUCT_DATA,
    )

    assert response.status_code == 401

    print(
        "✓ Create product authentication test passed"
    )


# ==========================================
# Customer Cannot Create Product
# ==========================================

def test_customer_cannot_create_product(
    client,
    db,
):
    headers = create_customer_headers(db)

    response = client.post(
        "/products",
        json=PRODUCT_DATA,
        headers=headers,
    )

    assert response.status_code == 403

    data = response.json()

    assert (
        data["detail"]
        == "Administrator access required."
    )

    print(
        "✓ Customer create restriction test passed"
    )


# ==========================================
# Get All Products
# ==========================================

def test_get_products(
    client,
    db,
):
    product = create_test_product(db)

    response = client.get(
        "/products",
    )

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)
    assert len(data) >= 1

    product_ids = [
        item["id"]
        for item in data
    ]

    assert product.id in product_ids

    print(
        "✓ Public get products route test passed"
    )


# ==========================================
# Get Product By ID
# ==========================================

def test_get_product_by_id(
    client,
    db,
):
    product = create_test_product(db)

    response = client.get(
        f"/products/{product.id}",
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == product.id
    assert data["name"] == PRODUCT_DATA["name"]
    assert data["team"] == PRODUCT_DATA["team"]

    print(
        "✓ Public get product by ID test passed"
    )


# ==========================================
# Get Nonexistent Product
# ==========================================

def test_get_nonexistent_product(
    client,
):
    response = client.get(
        "/products/999999",
    )

    assert response.status_code == 404

    data = response.json()

    assert data["detail"] == "Product not found."

    print(
        "✓ Get nonexistent product route test passed"
    )


# ==========================================
# Update Product
# ==========================================

def test_update_product(
    client,
    db,
):
    product = create_test_product(db)
    headers = create_admin_headers(db)

    update_data = {
        "price": "79.99",
        "rating": 4.8,
        "in_stock": False,
    }

    response = client.patch(
        f"/products/{product.id}",
        json=update_data,
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == product.id
    assert Decimal(data["price"]) == Decimal(
        "79.99"
    )
    assert data["rating"] == 4.8
    assert data["in_stock"] is False

    assert data["name"] == PRODUCT_DATA["name"]
    assert data["team"] == PRODUCT_DATA["team"]

    print(
        "✓ Admin update product route test passed"
    )


# ==========================================
# Partial Product Update
# ==========================================

def test_partial_product_update(
    client,
    db,
):
    product = create_test_product(db)
    headers = create_admin_headers(db)

    response = client.patch(
        f"/products/{product.id}",
        json={
            "is_featured": False,
        },
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == product.id
    assert data["is_featured"] is False

    assert data["name"] == PRODUCT_DATA["name"]
    assert Decimal(data["price"]) == Decimal(
        "89.99"
    )
    assert data["team"] == PRODUCT_DATA["team"]

    print(
        "✓ Partial product update route test passed"
    )


# ==========================================
# Update Requires Authentication
# ==========================================

def test_update_product_requires_authentication(
    client,
    db,
):
    product = create_test_product(db)

    response = client.patch(
        f"/products/{product.id}",
        json={
            "price": "79.99",
        },
    )

    assert response.status_code == 401

    print(
        "✓ Update product authentication test passed"
    )


# ==========================================
# Customer Cannot Update Product
# ==========================================

def test_customer_cannot_update_product(
    client,
    db,
):
    product = create_test_product(db)
    headers = create_customer_headers(db)

    response = client.patch(
        f"/products/{product.id}",
        json={
            "price": "79.99",
        },
        headers=headers,
    )

    assert response.status_code == 403

    data = response.json()

    assert (
        data["detail"]
        == "Administrator access required."
    )

    print(
        "✓ Customer update restriction test passed"
    )


# ==========================================
# Update Nonexistent Product
# ==========================================

def test_update_nonexistent_product(
    client,
    db,
):
    headers = create_admin_headers(db)

    response = client.patch(
        "/products/999999",
        json={
            "price": "79.99",
        },
        headers=headers,
    )

    assert response.status_code == 404

    data = response.json()

    assert data["detail"] == "Product not found."

    print(
        "✓ Update nonexistent product test passed"
    )


# ==========================================
# Delete Product
# ==========================================

def test_delete_product(
    client,
    db,
):
    product = create_test_product(db)
    headers = create_admin_headers(db)

    response = client.delete(
        f"/products/{product.id}",
        headers=headers,
    )

    assert response.status_code == 204
    assert response.content == b""

    get_response = client.get(
        f"/products/{product.id}",
    )

    assert get_response.status_code == 404

    print(
        "✓ Admin delete product route test passed"
    )


# ==========================================
# Delete Requires Authentication
# ==========================================

def test_delete_product_requires_authentication(
    client,
    db,
):
    product = create_test_product(db)

    response = client.delete(
        f"/products/{product.id}",
    )

    assert response.status_code == 401

    print(
        "✓ Delete product authentication test passed"
    )


# ==========================================
# Customer Cannot Delete Product
# ==========================================

def test_customer_cannot_delete_product(
    client,
    db,
):
    product = create_test_product(db)
    headers = create_customer_headers(db)

    response = client.delete(
        f"/products/{product.id}",
        headers=headers,
    )

    assert response.status_code == 403

    data = response.json()

    assert (
        data["detail"]
        == "Administrator access required."
    )

    print(
        "✓ Customer delete restriction test passed"
    )


# ==========================================
# Delete Nonexistent Product
# ==========================================

def test_delete_nonexistent_product(
    client,
    db,
):
    headers = create_admin_headers(db)

    response = client.delete(
        "/products/999999",
        headers=headers,
    )

    assert response.status_code == 404

    data = response.json()

    assert data["detail"] == "Product not found."

    print(
        "✓ Delete nonexistent product test passed"
    )