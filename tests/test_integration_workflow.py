from decimal import Decimal

from fastapi.testclient import TestClient


def test_complete_customer_purchase_workflow(client: TestClient):
    """
    Verify the complete customer purchase workflow:

    Register
        -> Login
        -> Get current user
        -> Get products
        -> Get cart
        -> Add product
        -> Update quantity
        -> Verify cart
        -> Create order
        -> Verify order
        -> Verify cart is empty
        -> Get orders
        -> Get individual order
    """

    # ==========================================
    # 1. Register Customer
    # ==========================================

    register_payload = {
        "first_name": "Integration",
        "last_name": "Customer",
        "email": "integration.workflow@example.com",
        "password": "IntegrationPass123!",
        "confirm_password": "IntegrationPass123!",
    }

    register_response = client.post(
        "/auth/register",
        json=register_payload,
    )

    # The test database persists for the pytest session.
    # Registration may therefore return 409 if the user
    # already exists from an earlier test run.
    assert register_response.status_code in (201, 409)

    if register_response.status_code == 409:
        assert (
            "already"
            in register_response.json()["detail"].lower()
        )

    # ==========================================
    # 2. Login
    # ==========================================

    login_response = client.post(
        "/auth/login",
        json={
            "email": register_payload["email"],
            "password": register_payload["password"],
        },
    )

    assert login_response.status_code == 200

    login_data = login_response.json()

    assert "access_token" in login_data
    assert login_data["token_type"] == "bearer"

    access_token = login_data["access_token"]

    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    # ==========================================
    # 3. Get Current User
    # ==========================================

    me_response = client.get(
        "/auth/me",
        headers=headers,
    )

    assert me_response.status_code == 200

    me_data = me_response.json()

    assert me_data["email"] == register_payload["email"]
    assert me_data["first_name"] == register_payload["first_name"]
    assert me_data["last_name"] == register_payload["last_name"]

    # ==========================================
    # 4. Get Products
    # ==========================================

    products_response = client.get(
        "/products",
        headers=headers,
    )

    assert products_response.status_code == 200

    products_data = products_response.json()

    assert isinstance(products_data, list)
    assert len(products_data) > 0

    product = next(
        (
            item
            for item in products_data
            if item.get("in_stock") is True
        ),
        None,
    )

    assert product is not None

    product_id = product["id"]
    product_price = Decimal(str(product["price"]))

    # ==========================================
    # 5. Get Cart
    # ==========================================

    cart_response = client.get(
        "/cart",
        headers=headers,
    )

    assert cart_response.status_code == 200

    cart_data = cart_response.json()

    assert cart_data["user_id"] == me_data["id"]
    assert "items" in cart_data
    assert isinstance(cart_data["items"], list)

    # ==========================================
    # 6. Add Product To Cart
    # ==========================================

    add_item_response = client.post(
        "/cart/items",
        headers=headers,
        json={
            "product_id": product_id,
            "quantity": 2,
        },
    )

    assert add_item_response.status_code in (200, 201)

    added_item = add_item_response.json()

    assert added_item["product_id"] == product_id
    assert added_item["quantity"] >= 2

    item_id = added_item["id"]

    # ==========================================
    # 7. Update Cart Quantity
    # ==========================================

    update_response = client.patch(
        f"/cart/items/{item_id}",
        headers=headers,
        json={
            "quantity": 3,
        },
    )

    assert update_response.status_code == 200

    updated_item = update_response.json()

    assert updated_item["id"] == item_id
    assert updated_item["product_id"] == product_id
    assert updated_item["quantity"] == 3

    # ==========================================
    # 8. Verify Cart
    # ==========================================

    cart_response = client.get(
        "/cart",
        headers=headers,
    )

    assert cart_response.status_code == 200

    cart_data = cart_response.json()

    matching_items = [
        item
        for item in cart_data["items"]
        if item["id"] == item_id
    ]

    assert len(matching_items) == 1

    cart_item = matching_items[0]

    assert cart_item["product_id"] == product_id
    assert cart_item["quantity"] == 3

    expected_cart_subtotal = product_price * 3

    assert Decimal(str(cart_item["unit_price"])) == product_price
    assert Decimal(str(cart_item["subtotal"])) == expected_cart_subtotal

    # ==========================================
    # 9. Create Order From Cart
    # ==========================================

    order_response = client.post(
        "/orders",
        headers=headers,
    )

    assert order_response.status_code in (200, 201)

    order_data = order_response.json()

    assert order_data["user_id"] == me_data["id"]
    assert order_data["status"] == "pending"

    order_id = order_data["id"]

    # ==========================================
    # 10. Verify Order Items
    # ==========================================

    assert "items" in order_data
    assert isinstance(order_data["items"], list)
    assert len(order_data["items"]) == 1

    order_item = order_data["items"][0]

    assert order_item["product_id"] == product_id
    assert order_item["quantity"] == 3

    assert Decimal(str(order_item["unit_price"])) == product_price

    expected_subtotal = product_price * 3

    assert Decimal(str(order_item["subtotal"])) == expected_subtotal

    assert Decimal(str(order_data["total_amount"])) == expected_subtotal

    # ==========================================
    # 11. Verify Cart Is Empty
    # ==========================================

    cart_response = client.get(
        "/cart",
        headers=headers,
    )

    assert cart_response.status_code == 200

    cart_data = cart_response.json()

    assert cart_data["items"] == []

    # ==========================================
    # 12. Get Customer Orders
    # ==========================================

    orders_response = client.get(
        "/orders",
        headers=headers,
    )

    assert orders_response.status_code == 200

    orders_data = orders_response.json()

    assert isinstance(orders_data, list)
    assert len(orders_data) >= 1

    order_ids = [
        order["id"]
        for order in orders_data
    ]

    assert order_id in order_ids

    # ==========================================
    # 13. Get Individual Order
    # ==========================================

    individual_order_response = client.get(
        f"/orders/{order_id}",
        headers=headers,
    )

    assert individual_order_response.status_code == 200

    individual_order = individual_order_response.json()

    assert individual_order["id"] == order_id
    assert individual_order["user_id"] == me_data["id"]
    assert individual_order["status"] == "pending"

    assert (
        Decimal(str(individual_order["total_amount"]))
        == expected_subtotal
    )

    assert len(individual_order["items"]) == 1
    assert individual_order["items"][0]["product_id"] == product_id
    assert individual_order["items"][0]["quantity"] == 3


def test_customer_cannot_access_another_users_order(
    client: TestClient,
):
    """
    Verify order ownership protection.

    Customer A creates an order.
    Customer B attempts to access it.
    Customer B must receive HTTP 403.
    """

    # ==========================================
    # Customer A - Register
    # ==========================================

    customer_a = {
        "first_name": "Customer",
        "last_name": "Alpha",
        "email": "integration.alpha@example.com",
        "password": "IntegrationPass123!",
        "confirm_password": "IntegrationPass123!",
    }

    register_a = client.post(
        "/auth/register",
        json=customer_a,
    )

    assert register_a.status_code in (201, 409)

    if register_a.status_code == 409:
        assert (
            "already"
            in register_a.json()["detail"].lower()
        )

    # ==========================================
    # Customer A - Login
    # ==========================================

    login_a = client.post(
        "/auth/login",
        json={
            "email": customer_a["email"],
            "password": customer_a["password"],
        },
    )

    assert login_a.status_code == 200

    token_a = login_a.json()["access_token"]

    headers_a = {
        "Authorization": f"Bearer {token_a}",
    }

    # ==========================================
    # Customer A - Get Product
    # ==========================================

    products_response = client.get(
        "/products",
        headers=headers_a,
    )

    assert products_response.status_code == 200

    products = products_response.json()

    product = next(
        (
            item
            for item in products
            if item.get("in_stock") is True
        ),
        None,
    )

    assert product is not None

    # ==========================================
    # Customer A - Add Product
    # ==========================================

    add_response = client.post(
        "/cart/items",
        headers=headers_a,
        json={
            "product_id": product["id"],
            "quantity": 1,
        },
    )

    assert add_response.status_code in (200, 201)

    # ==========================================
    # Customer A - Create Order
    # ==========================================

    order_response = client.post(
        "/orders",
        headers=headers_a,
    )

    assert order_response.status_code in (200, 201)

    order_id = order_response.json()["id"]

    # ==========================================
    # Customer B - Register
    # ==========================================

    customer_b = {
        "first_name": "Customer",
        "last_name": "Beta",
        "email": "integration.beta@example.com",
        "password": "IntegrationPass123!",
        "confirm_password": "IntegrationPass123!",
    }

    register_b = client.post(
        "/auth/register",
        json=customer_b,
    )

    assert register_b.status_code in (201, 409)

    if register_b.status_code == 409:
        assert (
            "already"
            in register_b.json()["detail"].lower()
        )

    # ==========================================
    # Customer B - Login
    # ==========================================

    login_b = client.post(
        "/auth/login",
        json={
            "email": customer_b["email"],
            "password": customer_b["password"],
        },
    )

    assert login_b.status_code == 200

    token_b = login_b.json()["access_token"]

    headers_b = {
        "Authorization": f"Bearer {token_b}",
    }

    # ==========================================
    # Customer B - Attempt To Access
    # Customer A's Order
    # ==========================================

    unauthorized_response = client.get(
        f"/orders/{order_id}",
        headers=headers_b,
    )

    assert unauthorized_response.status_code == 403