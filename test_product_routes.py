from decimal import Decimal


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
# Create Product
# ==========================================

def test_create_product(client):
    response = client.post(
        "/products",
        json=PRODUCT_DATA,
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
    assert Decimal(data["price"]) == Decimal("89.99")
    assert Decimal(data["old_price"]) == Decimal("109.99")
    assert data["rating"] == 4.5
    assert data["is_featured"] is True
    assert data["is_new"] is True
    assert data["is_best_seller"] is False
    assert data["in_stock"] is True

    print("✓ Create product route test passed")


# ==========================================
# Get All Products
# ==========================================

def test_get_products(client):
    create_response = client.post(
        "/products",
        json=PRODUCT_DATA,
    )

    assert create_response.status_code == 201

    created_product = create_response.json()

    response = client.get(
        "/products"
    )

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)
    assert len(data) >= 1

    product_ids = [
        product["id"]
        for product in data
    ]

    assert created_product["id"] in product_ids

    print("✓ Get products route test passed")


# ==========================================
# Get Product By ID
# ==========================================

def test_get_product_by_id(client):
    create_response = client.post(
        "/products",
        json=PRODUCT_DATA,
    )

    assert create_response.status_code == 201

    product_id = create_response.json()["id"]

    response = client.get(
        f"/products/{product_id}"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == product_id
    assert data["name"] == PRODUCT_DATA["name"]
    assert data["team"] == PRODUCT_DATA["team"]

    print("✓ Get product by ID route test passed")


# ==========================================
# Get Nonexistent Product
# ==========================================

def test_get_nonexistent_product(client):
    response = client.get(
        "/products/999999"
    )

    assert response.status_code == 404

    data = response.json()

    assert data["detail"] == "Product not found."

    print("✓ Get nonexistent product route test passed")


# ==========================================
# Update Product
# ==========================================

def test_update_product(client):
    create_response = client.post(
        "/products",
        json=PRODUCT_DATA,
    )

    assert create_response.status_code == 201

    product_id = create_response.json()["id"]

    update_data = {
        "price": "79.99",
        "rating": 4.8,
        "in_stock": False,
    }

    response = client.patch(
        f"/products/{product_id}",
        json=update_data,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == product_id
    assert Decimal(data["price"]) == Decimal("79.99")
    assert data["rating"] == 4.8
    assert data["in_stock"] is False

    # Verify that fields not included in the
    # update remain unchanged.
    assert data["name"] == PRODUCT_DATA["name"]
    assert data["team"] == PRODUCT_DATA["team"]

    print("✓ Update product route test passed")


# ==========================================
# Partial Product Update
# ==========================================

def test_partial_product_update(client):
    create_response = client.post(
        "/products",
        json=PRODUCT_DATA,
    )

    assert create_response.status_code == 201

    created_product = create_response.json()
    product_id = created_product["id"]

    response = client.patch(
        f"/products/{product_id}",
        json={
            "is_featured": False,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == product_id
    assert data["is_featured"] is False

    # Other fields must remain unchanged.
    assert data["name"] == PRODUCT_DATA["name"]
    assert Decimal(data["price"]) == Decimal("89.99")
    assert data["team"] == PRODUCT_DATA["team"]

    print("✓ Partial product update route test passed")


# ==========================================
# Update Nonexistent Product
# ==========================================

def test_update_nonexistent_product(client):
    response = client.patch(
        "/products/999999",
        json={
            "price": "79.99",
        },
    )

    assert response.status_code == 404

    data = response.json()

    assert data["detail"] == "Product not found."

    print("✓ Update nonexistent product route test passed")


# ==========================================
# Delete Product
# ==========================================

def test_delete_product(client):
    create_response = client.post(
        "/products",
        json=PRODUCT_DATA,
    )

    assert create_response.status_code == 201

    product_id = create_response.json()["id"]

    response = client.delete(
        f"/products/{product_id}"
    )

    assert response.status_code == 204
    assert response.content == b""

    # Confirm that the product is actually gone.
    get_response = client.get(
        f"/products/{product_id}"
    )

    assert get_response.status_code == 404

    print("✓ Delete product route test passed")


# ==========================================
# Delete Nonexistent Product
# ==========================================

def test_delete_nonexistent_product(client):
    response = client.delete(
        "/products/999999"
    )

    assert response.status_code == 404

    data = response.json()

    assert data["detail"] == "Product not found."

    print("✓ Delete nonexistent product route test passed")