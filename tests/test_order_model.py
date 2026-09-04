from decimal import Decimal

from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.product import Product
from app.models.user import User


# ==========================================
# Test Helpers
# ==========================================

def create_test_user(
    db,
    email="order_test@example.com",
):
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
    db,
    name="Order Test Jersey",
):
    product = Product(
        name=name,
        sport="Football",
        category="Jerseys",
        team="Manchester United",
        league="Premier League",
        brand="Adidas",
        price=Decimal("89.99"),
        old_price=Decimal("109.99"),
        rating=Decimal("4.50"),
        image="/images/order-test.jpg",
        is_featured=False,
        is_new=True,
        is_best_seller=False,
        in_stock=True,
    )

    db.add(product)
    db.commit()
    db.refresh(product)

    return product


# ==========================================
# Create Order
# ==========================================

def test_create_order(db):
    user = create_test_user(
        db,
        email="create_order@example.com",
    )

    order = Order(
        user_id=user.id,
    )

    db.add(order)
    db.commit()
    db.refresh(order)

    assert order.id is not None
    assert order.user_id == user.id
    assert order.status == "pending"
    assert order.total_amount == Decimal("0.00")

    print("✓ Create order model test passed")


# ==========================================
# Order User Relationship
# ==========================================

def test_order_user_relationship(db):
    user = create_test_user(
        db,
        email="order_user_relationship@example.com",
    )

    order = Order(
        user_id=user.id,
    )

    db.add(order)
    db.commit()
    db.refresh(order)

    assert order.user is not None
    assert order.user.id == user.id
    assert order.user.email == user.email

    print("✓ Order user relationship test passed")


# ==========================================
# Create Order Item
# ==========================================

def test_create_order_item(db):
    user = create_test_user(
        db,
        email="create_order_item@example.com",
    )

    product = create_test_product(db)

    order = Order(
        user_id=user.id,
        total_amount=Decimal("179.98"),
    )

    db.add(order)
    db.commit()
    db.refresh(order)

    item = OrderItem(
        order_id=order.id,
        product_id=product.id,
        quantity=2,
        unit_price=Decimal("89.99"),
        subtotal=Decimal("179.98"),
    )

    db.add(item)
    db.commit()
    db.refresh(item)

    assert item.id is not None
    assert item.order_id == order.id
    assert item.product_id == product.id
    assert item.quantity == 2
    assert item.unit_price == Decimal("89.99")
    assert item.subtotal == Decimal("179.98")

    print("✓ Create order item model test passed")


# ==========================================
# Order Items Relationship
# ==========================================

def test_order_items_relationship(db):
    user = create_test_user(
        db,
        email="order_items_relationship@example.com",
    )

    product_one = create_test_product(
        db,
        name="Manchester United Jersey",
    )

    product_two = create_test_product(
        db,
        name="Real Madrid Jersey",
    )

    order = Order(
        user_id=user.id,
        total_amount=Decimal("269.97"),
    )

    db.add(order)
    db.commit()
    db.refresh(order)

    item_one = OrderItem(
        order_id=order.id,
        product_id=product_one.id,
        quantity=1,
        unit_price=Decimal("89.99"),
        subtotal=Decimal("89.99"),
    )

    item_two = OrderItem(
        order_id=order.id,
        product_id=product_two.id,
        quantity=2,
        unit_price=Decimal("89.99"),
        subtotal=Decimal("179.98"),
    )

    db.add_all([item_one, item_two])
    db.commit()
    db.refresh(order)

    assert len(order.items) == 2

    product_ids = {
        item.product_id
        for item in order.items
    }

    assert product_one.id in product_ids
    assert product_two.id in product_ids

    print("✓ Order items relationship test passed")


# ==========================================
# Order Item Product Relationship
# ==========================================

def test_order_item_product_relationship(db):
    user = create_test_user(
        db,
        email="order_product_relationship@example.com",
    )

    product = create_test_product(db)

    order = Order(
        user_id=user.id,
    )

    db.add(order)
    db.commit()
    db.refresh(order)

    item = OrderItem(
        order_id=order.id,
        product_id=product.id,
        quantity=1,
        unit_price=product.price,
        subtotal=product.price,
    )

    db.add(item)
    db.commit()
    db.refresh(item)

    assert item.product is not None
    assert item.product.id == product.id
    assert item.product.name == product.name

    print("✓ Order item product relationship test passed")


# ==========================================
# Order Cascade Delete
# ==========================================

def test_order_cascade_delete(db):
    user = create_test_user(
        db,
        email="order_cascade@example.com",
    )

    product = create_test_product(
        db,
        name="Order Cascade Jersey",
    )

    order = Order(
        user_id=user.id,
    )

    db.add(order)
    db.commit()
    db.refresh(order)

    item = OrderItem(
        order_id=order.id,
        product_id=product.id,
        quantity=1,
        unit_price=Decimal("89.99"),
        subtotal=Decimal("89.99"),
    )

    db.add(item)
    db.commit()
    db.refresh(item)

    order_id = order.id
    item_id = item.id

    db.delete(order)
    db.commit()

    deleted_order = db.get(
        Order,
        order_id,
    )

    deleted_item = db.get(
        OrderItem,
        item_id,
    )

    assert deleted_order is None
    assert deleted_item is None

    print("✓ Order cascade delete test passed")
    
