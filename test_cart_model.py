from decimal import Decimal

from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.models.product import Product
from app.models.user import User


# ==========================================
# Test Helpers
# ==========================================

def create_test_user(
    db,
    email="cart_test@example.com",
):
    user = User(
        first_name="Cart",
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
    name="Test Football Jersey",
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
        image="/images/test-jersey.jpg",
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
# Create Cart
# ==========================================

def test_create_cart(db):
    user = create_test_user(
        db,
        email="create_cart@example.com",
    )

    cart = Cart(
        user_id=user.id,
    )

    db.add(cart)
    db.commit()
    db.refresh(cart)

    assert cart.id is not None
    assert cart.user_id == user.id
    assert cart.user.id == user.id

    print("✓ Create cart model test passed")


# ==========================================
# Cart User Relationship
# ==========================================

def test_cart_user_relationship(db):
    user = create_test_user(
        db,
        email="cart_user_relationship@example.com",
    )

    cart = Cart(
        user_id=user.id,
    )

    db.add(cart)
    db.commit()
    db.refresh(cart)

    assert cart.user is not None
    assert cart.user.id == user.id
    assert cart.user.email == user.email

    print("✓ Cart user relationship test passed")


# ==========================================
# Add Cart Item
# ==========================================

def test_add_cart_item(db):
    user = create_test_user(
        db,
        email="add_cart_item@example.com",
    )

    product = create_test_product(db)

    cart = Cart(
        user_id=user.id,
    )

    db.add(cart)
    db.commit()
    db.refresh(cart)

    item = CartItem(
        cart_id=cart.id,
        product_id=product.id,
        quantity=2,
    )

    db.add(item)
    db.commit()
    db.refresh(item)

    assert item.id is not None
    assert item.cart_id == cart.id
    assert item.product_id == product.id
    assert item.quantity == 2

    assert item.cart.id == cart.id
    assert item.product.id == product.id

    print("✓ Add cart item model test passed")


# ==========================================
# Cart Items Relationship
# ==========================================

def test_cart_items_relationship(db):
    user = create_test_user(
        db,
        email="cart_items_relationship@example.com",
    )

    product_one = create_test_product(
        db,
        name="Manchester United Jersey",
    )

    product_two = create_test_product(
        db,
        name="Real Madrid Jersey",
    )

    cart = Cart(
        user_id=user.id,
    )

    db.add(cart)
    db.commit()
    db.refresh(cart)

    item_one = CartItem(
        cart_id=cart.id,
        product_id=product_one.id,
        quantity=1,
    )

    item_two = CartItem(
        cart_id=cart.id,
        product_id=product_two.id,
        quantity=2,
    )

    db.add_all([item_one, item_two])
    db.commit()
    db.refresh(cart)

    assert len(cart.items) == 2

    product_ids = {
        item.product_id
        for item in cart.items
    }

    assert product_one.id in product_ids
    assert product_two.id in product_ids

    print("✓ Cart items relationship test passed")


# ==========================================
# Cart Cascade Delete
# ==========================================

def test_cart_cascade_delete(db):
    user = create_test_user(
        db,
        email="cart_cascade@example.com",
    )

    product = create_test_product(
        db,
        name="Cascade Test Jersey",
    )

    cart = Cart(
        user_id=user.id,
    )

    db.add(cart)
    db.commit()
    db.refresh(cart)

    item = CartItem(
        cart_id=cart.id,
        product_id=product.id,
        quantity=1,
    )

    db.add(item)
    db.commit()
    db.refresh(item)

    item_id = item.id
    cart_id = cart.id

    db.delete(cart)
    db.commit()

    deleted_cart = db.get(
        Cart,
        cart_id,
    )

    deleted_item = db.get(
        CartItem,
        item_id,
    )

    assert deleted_cart is None
    assert deleted_item is None

    print("✓ Cart cascade delete test passed")
