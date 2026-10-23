from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy.engine import make_url

from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.payment import Payment
from app.models.product import Product
from app.models.user import User
from app.utils.security import create_access_token


def headers(user):
    return {"Authorization": f"Bearer {create_access_token({'sub': str(user.id)})}"}


@pytest.fixture
def actors(db):
    return (
        db.query(User).filter(User.role == "admin").first(),
        db.query(User).filter(User.role == "customer").first(),
    )


def test_all_management_surfaces_require_active_admin(client, db, actors):
    admin, customer = actors
    product = db.query(Product).first()
    operations = [
        ("GET", "/admin/overview", None),
        ("GET", "/admin/customers", None),
        ("GET", "/admin/orders/page", None),
        ("GET", "/admin/orders/1", None),
        ("GET", "/admin/orders", None),
        ("PATCH", "/admin/orders/1", {"status": "processing"}),
        ("PUT", f"/admin/inventory/{product.id}", {
            "stock_quantity": 2, "in_stock": True,
            "expected_stock_quantity": None, "expected_in_stock": True,
        }),
        ("POST", "/products", {
            "name": "Forbidden product", "sport": "Football",
            "category": "Jerseys", "price": "20.00",
        }),
        ("PATCH", f"/products/{product.id}", {"price": "1.00"}),
        ("DELETE", f"/products/{product.id}", None),
    ]
    initial = (product.price, product.stock_quantity, db.query(Product).count())
    for auth in ({}, headers(customer)):
        for method, path, payload in operations:
            response = client.request(method, path, json=payload, headers=auth)
            assert response.status_code in (401, 403), (path, response.text)
    # The server checks the current role, not a stale token claim.
    token = headers(admin)
    admin.role = "customer"
    db.commit()
    assert client.get("/admin/customers", headers=token).status_code == 403
    admin.role = "admin"
    admin.is_active = False
    db.commit()
    assert client.get("/admin/overview", headers=token).status_code == 403
    db.refresh(product)
    assert (product.price, product.stock_quantity, db.query(Product).count()) == initial


def test_metrics_count_only_matching_verified_orders_once(client, db, actors):
    admin, customer = actors
    products = db.query(Product).order_by(Product.id).all()
    for product in products:
        product.in_stock = True
        product.stock_quantity = 10
    for product, qty in zip(products, [0, 1, 5, 6, None]):
        product.stock_quantity = qty
    products[5].in_stock = False
    statuses = ["paid", "processing", "paid", "pending", "cancelled", "paid", "paid", "paid", "paid"]
    orders = []
    for index, status in enumerate(statuses, 1):
        order = Order(user_id=customer.id, status=status, total_amount=Decimal(index * 100))
        db.add(order)
        db.flush()
        orders.append(order)
    def payment(index, ref, **overrides):
        data = dict(
            order_id=orders[index].id, user_id=customer.id, amount=orders[index].total_amount,
            reference=ref, status="success", provider="paystack", currency="NGN",
        )
        data.update(overrides)
        db.add(Payment(**data))
    payment(0, "verified-one")
    payment(1, "verified-two")
    payment(1, "duplicate-success")
    payment(3, "failed", status="failed")
    payment(4, "cancelled-verified")
    payment(5, "wrong-amount", amount=Decimal("1.00"))
    payment(6, "wrong-currency", currency="USD")
    payment(7, "wrong-owner", user_id=admin.id)
    payment(8, "wrong-provider", provider="other")
    db.commit()
    response = client.get("/admin/overview", headers=headers(admin))
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["sales"] == {
        "verified_orders": 2, "verified_sales_ngn": "300.00",
        "cancelled_verified_orders": 1, "cancelled_verified_ngn": "500.00",
    }
    assert data["total_orders"] == 9
    assert data["awaiting_processing"] == 1
    assert data["inventory"] == {
        "total": len(products), "in_stock": len(products) - 2,
        "out_of_stock": 2, "low_stock": 2, "uncounted": 1,
        "low_stock_threshold": 5,
    }
    assert len(data["recent_orders"]) == 5
    assert data["recent_orders"][0]["payment_status"] == "inconsistent"
    verified = client.get(
        "/admin/orders/page?payment_status=verified&page_size=2", headers=headers(admin)
    ).json()
    assert verified["total"] == 3 and len(verified["items"]) == 2
    assert "password_hash" not in response.text
    assert "provider_transaction_id" not in response.text


def test_customer_search_order_pagination_and_sensitive_data_projection(client, db, actors):
    admin, customer = actors
    orders = [
        Order(user_id=customer.id, total_amount=Decimal("100.00"), status=s)
        for s in ("pending", "paid", "shipped")
    ]
    db.add_all(orders)
    db.commit()
    auth = headers(admin)
    customers = client.get("/admin/customers?q=sample", headers=auth)
    assert customers.status_code == 200
    row = next(c for c in customers.json()["items"] if c["id"] == customer.id)
    assert row["order_count"] == 3
    assert set(row) == {"id", "first_name", "last_name", "email", "is_active", "order_count"}
    response = client.get(
        f"/admin/orders/page?customer_id={customer.id}&page_size=1&page=2", headers=auth
    ).json()
    assert response["total"] == 3 and response["page"] == 2
    assert len(response["items"]) == 1
    assert client.get(
        "/admin/orders/page?status=shipped", headers=auth
    ).json()["total"] == 1
    assert client.get(
        f"/admin/orders/page?q=%23{orders[0].id}", headers=auth
    ).json()["total"] == 1
    assert client.get("/admin/orders/page?q=%25", headers=auth).json()["total"] == 0
    for path in (
        "/admin/orders/page?page_size=101", "/admin/orders/page?page=0",
        "/admin/orders/page?status=invented", "/admin/customers?page=-1",
    ):
        assert client.get(path, headers=auth).status_code == 422


def test_product_changes_persist_and_order_price_snapshots_are_preserved(client, db, actors):
    admin, customer = actors
    auth = headers(admin)
    created = client.post("/products", headers=auth, json={
        "name": "Managed test jersey", "sport": "Football", "category": "Jerseys",
        "description": "Published by an operator", "price": "25000.00",
        "old_price": "30000.00", "image": "/images/products/football/chelsea-home.webp",
    })
    assert created.status_code == 201, created.text
    product_id = created.json()["id"]
    order = Order(user_id=customer.id, status="pending", total_amount=Decimal("25000.00"))
    db.add(order)
    db.flush()
    item = OrderItem(
        order_id=order.id, product_id=product_id, quantity=1,
        unit_price=Decimal("25000.00"), subtotal=Decimal("25000.00"),
    )
    db.add(item)
    db.commit()
    updated = client.patch(f"/products/{product_id}", headers=auth, json={
        "price": "26000.00", "description": "Updated description",
        "image": "/images/products/football/manchester-united-home22.jpg",
    })
    assert updated.status_code == 200
    public = client.get(f"/products/{product_id}").json()
    assert public["price"] == "26000.00" and public["description"] == "Updated description"
    assert public["image"].endswith("manchester-united-home22.jpg")
    details = client.get(f"/admin/orders/{order.id}", headers=auth)
    assert details.status_code == 200, details.text
    assert details.json()["items"][0]["unit_price"] == "25000.00"
    assert details.json()["available_actions"] == ["cancelled"]
    assert client.patch(f"/admin/orders/{order.id}", headers=auth, json={
        "status": "paid",
    }).status_code == 400
    assert client.patch(f"/admin/orders/{order.id}", headers=auth, json={
        "status": "processing", "payment_status": "success",
    }).status_code == 422


@pytest.mark.parametrize("payload", [
    {"image": "https://example.com/photo.jpg"},
    {"image": "/images/../private.jpg"},
    {"image": "/images/a.webp?x=1"},
    {"image": "javascript:alert(1)"},
    {"gallery": ["/images/products/a.jpg"]},
    {"name": "   "},
    {"price": None},
    {"in_stock": None},
    {"stock_quantity": -1},
    {"stock_quantity": 1.5},
    {"stock_quantity": 2147483648},
])
def test_product_write_validation(client, db, actors, payload):
    product = db.query(Product).first()
    response = client.patch(f"/products/{product.id}", headers=headers(actors[0]), json=payload)
    assert response.status_code == 422, response.text


def test_inventory_persistence_zero_handling_and_stale_write_conflict(client, db, actors):
    auth = headers(actors[0])
    product = db.query(Product).first()
    product.stock_quantity = 3
    product.in_stock = True
    db.commit()
    payload = {
        "stock_quantity": 4, "in_stock": True,
        "expected_stock_quantity": 3, "expected_in_stock": True,
    }
    path = f"/admin/inventory/{product.id}"
    response = client.put(path, headers=auth, json=payload)
    assert response.status_code == 200 and response.json()["stock_quantity"] == 4
    assert client.put(path, headers=auth, json=payload).status_code == 409
    assert client.get(f"/products/{product.id}").json()["stock_quantity"] == 4
    payload["expected_stock_quantity"] = 4
    payload["stock_quantity"] = -1
    assert client.put(path, headers=auth, json=payload).status_code == 422
    payload["stock_quantity"] = 0
    response = client.put(path, headers=auth, json=payload)
    assert response.json()["in_stock"] is False
    payload.update(stock_quantity=None, expected_stock_quantity=0, expected_in_stock=False)
    response = client.put(path, headers=auth, json=payload)
    assert response.json()["stock_quantity"] is None and response.json()["in_stock"] is True


def test_order_actions_cannot_skip_fulfilment_or_modify_payment(client, db, actors):
    admin, customer = actors
    order = Order(user_id=customer.id, status="paid", total_amount=Decimal("100.00"))
    db.add(order)
    db.flush()
    payment = Payment(
        order_id=order.id, user_id=customer.id, amount=Decimal("100.00"),
        reference="immutable-payment", status="success", currency="NGN",
    )
    db.add(payment)
    db.commit()
    path = f"/admin/orders/{order.id}"
    auth = headers(admin)
    assert client.patch(path, headers=auth, json={"status": "delivered"}).status_code == 400
    for target in ("processing", "shipped", "delivered"):
        assert client.patch(path, headers=auth, json={"status": target}).status_code == 200
    assert client.patch(path, headers=auth, json={"status": "cancelled"}).status_code == 400
    detail = client.get(path, headers=auth).json()
    assert detail["available_actions"] == [] and detail["payment_status"] == "success"
    db.refresh(payment)
    assert payment.status == "success" and payment.amount == Decimal("100.00")


def test_admin_provisioning_refuses_remote_database(monkeypatch):
    from scripts import provision_admin

    monkeypatch.setattr("sys.argv", [
        "provision_admin", "--user-id", "1", "--email", "owner@example.com", "--apply",
    ])
    monkeypatch.setattr(provision_admin, "engine", SimpleNamespace(
        url=make_url("postgresql://remote.example/ultimatekits")
    ))
    with pytest.raises(RuntimeError, match="local development"):
        provision_admin.main()
