from decimal import Decimal
import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.models.product import Product
from app.models.user import User
from app.schemas.cart import CartItemCreate, CartItemUpdate
from app.services.cart_service import CartService


# ==========================================
# Test Helpers
# ==========================================

def create_test_user(
    db: Session,
) -> User:
    """
    Create a temporary test user.
    """

    user = User(
        first_name="Cart",
        last_name="Test",
        email=(
            f"cart_{uuid.uuid4().hex[:8]}"
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
    name: str = "Test Football Jersey",
    price: Decimal = Decimal("89.99"),
    in_stock: bool = True,
) -> Product:
    """
    Create a temporary test product.
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


def create_cart(
    db: Session,
) -> tuple[User, Cart]:
    """
    Create a test user and cart.
    """

    user = create_test_user(db)

    cart = CartService.get_or_create_cart(
        db,
        user.id,
    )

    return user, cart


def test_sync_cart_replaces_items(
    db: Session,
):
    _, cart = create_cart(db)
    first_product = create_test_product(
        db,
        name="First Jersey",
    )
    second_product = create_test_product(
        db,
        name="Second Jersey",
    )

    CartService.add_item(
        db,
        cart,
        CartItemCreate(
            product_id=first_product.id,
            quantity=1,
        ),
    )

    result = CartService.sync_cart(
        db,
        cart,
        [
            CartItemCreate(
                product_id=second_product.id,
                quantity=2,
            ),
            CartItemCreate(
                product_id=second_product.id,
                quantity=1,
            ),
        ],
    )

    assert len(result.items) == 1
    assert result.items[0].product_id == second_product.id
    assert result.items[0].quantity == 3


def test_sync_cart_does_not_clear_on_validation_error(
    db: Session,
):
    _, cart = create_cart(db)
    product = create_test_product(db)
    CartService.add_item(
        db,
        cart,
        CartItemCreate(
            product_id=product.id,
            quantity=2,
        ),
    )

    with pytest.raises(HTTPException) as error:
        CartService.sync_cart(
            db,
            cart,
            [
                CartItemCreate(
                    product_id=999999,
                    quantity=1,
                )
            ],
        )

    assert error.value.status_code == 404
    db.expire(cart, ["items"])
    assert len(cart.items) == 1
    assert cart.items[0].product_id == product.id


# ==========================================
# Get Or Create Cart
# ==========================================

def test_get_or_create_cart_creates_cart(
    db: Session,
):
    user = create_test_user(db)

    cart = CartService.get_or_create_cart(
        db,
        user.id,
    )

    assert cart.id is not None
    assert cart.user_id == user.id
    assert cart.items == []

    print("✓ Get or create cart test passed")


def test_get_or_create_cart_returns_existing_cart(
    db: Session,
):
    user = create_test_user(db)

    first_cart = CartService.get_or_create_cart(
        db,
        user.id,
    )

    second_cart = CartService.get_or_create_cart(
        db,
        user.id,
    )

    assert second_cart.id == first_cart.id

    carts = (
        db.query(Cart)
        .filter(Cart.user_id == user.id)
        .all()
    )

    assert len(carts) == 1

    print("✓ Existing cart retrieval test passed")


# ==========================================
# Get Cart
# ==========================================

def test_get_cart(
    db: Session,
):
    user = create_test_user(db)

    cart = CartService.get_cart(
        db,
        user.id,
    )

    assert cart is not None
    assert cart.user_id == user.id

    print("✓ Get cart test passed")


# ==========================================
# Add Item To Cart
# ==========================================

def test_add_item(
    db: Session,
):
    user, cart = create_cart(db)

    product = create_test_product(db)

    data = CartItemCreate(
        product_id=product.id,
        quantity=2,
    )

    cart_item = CartService.add_item(
        db,
        cart,
        data,
    )

    assert cart_item.id is not None
    assert cart_item.cart_id == cart.id
    assert cart_item.product_id == product.id
    assert cart_item.quantity == 2

    print("✓ Add item test passed")


def test_add_existing_item_increases_quantity(
    db: Session,
):
    user, cart = create_cart(db)

    product = create_test_product(db)

    first_data = CartItemCreate(
        product_id=product.id,
        quantity=2,
    )

    first_item = CartService.add_item(
        db,
        cart,
        first_data,
    )

    second_data = CartItemCreate(
        product_id=product.id,
        quantity=3,
    )

    second_item = CartService.add_item(
        db,
        cart,
        second_data,
    )

    assert second_item.id == first_item.id
    assert second_item.quantity == 5

    items = (
        db.query(CartItem)
        .filter(CartItem.cart_id == cart.id)
        .all()
    )

    assert len(items) == 1

    print("✓ Existing item quantity test passed")


# ==========================================
# Add Nonexistent Product
# ==========================================

def test_add_nonexistent_product(
    db: Session,
):
    user, cart = create_cart(db)

    data = CartItemCreate(
        product_id=999999,
        quantity=1,
    )

    with pytest.raises(HTTPException) as error:
        CartService.add_item(
            db,
            cart,
            data,
        )

    assert error.value.status_code == 404
    assert error.value.detail == "Product not found."

    print("✓ Nonexistent product test passed")


# ==========================================
# Add Out Of Stock Product
# ==========================================

def test_add_out_of_stock_product(
    db: Session,
):
    user, cart = create_cart(db)

    product = create_test_product(
        db,
        in_stock=False,
    )

    data = CartItemCreate(
        product_id=product.id,
        quantity=1,
    )

    with pytest.raises(HTTPException) as error:
        CartService.add_item(
            db,
            cart,
            data,
        )

    assert error.value.status_code == 400
    assert error.value.detail == "Product is out of stock."

    print("✓ Out of stock product test passed")


# ==========================================
# Update Cart Item
# ==========================================

def test_update_item(
    db: Session,
):
    user, cart = create_cart(db)

    product = create_test_product(db)

    add_data = CartItemCreate(
        product_id=product.id,
        quantity=2,
    )

    cart_item = CartService.add_item(
        db,
        cart,
        add_data,
    )

    update_data = CartItemUpdate(
        quantity=5,
    )

    updated_item = CartService.update_item(
        db,
        cart,
        cart_item.id,
        update_data,
    )

    assert updated_item.id == cart_item.id
    assert updated_item.quantity == 5

    print("✓ Update cart item test passed")


# ==========================================
# Update Nonexistent Cart Item
# ==========================================

def test_update_nonexistent_item(
    db: Session,
):
    user, cart = create_cart(db)

    update_data = CartItemUpdate(
        quantity=5,
    )

    with pytest.raises(HTTPException) as error:
        CartService.update_item(
            db,
            cart,
            999999,
            update_data,
        )

    assert error.value.status_code == 404
    assert error.value.detail == "Cart item not found."

    print("✓ Update nonexistent cart item test passed")


# ==========================================
# Remove Cart Item
# ==========================================

def test_remove_item(
    db: Session,
):
    user, cart = create_cart(db)

    product = create_test_product(db)

    add_data = CartItemCreate(
        product_id=product.id,
        quantity=2,
    )

    cart_item = CartService.add_item(
        db,
        cart,
        add_data,
    )

    item_id = cart_item.id

    CartService.remove_item(
        db,
        cart,
        item_id,
    )

    deleted_item = (
        db.query(CartItem)
        .filter(CartItem.id == item_id)
        .first()
    )

    assert deleted_item is None

    print("✓ Remove cart item test passed")


# ==========================================
# Remove Nonexistent Cart Item
# ==========================================

def test_remove_nonexistent_item(
    db: Session,
):
    user, cart = create_cart(db)

    with pytest.raises(HTTPException) as error:
        CartService.remove_item(
            db,
            cart,
            999999,
        )

    assert error.value.status_code == 404
    assert error.value.detail == "Cart item not found."

    print("✓ Remove nonexistent cart item test passed")


# ==========================================
# Clear Cart
# ==========================================

def test_clear_cart(
    db: Session,
):
    user, cart = create_cart(db)

    product_one = create_test_product(
        db,
        name="Test Jersey One",
    )

    product_two = create_test_product(
        db,
        name="Test Jersey Two",
    )

    CartService.add_item(
        db,
        cart,
        CartItemCreate(
            product_id=product_one.id,
            quantity=2,
        ),
    )

    CartService.add_item(
        db,
        cart,
        CartItemCreate(
            product_id=product_two.id,
            quantity=3,
        ),
    )

    CartService.clear_cart(
        db,
        cart,
    )

    items = (
        db.query(CartItem)
        .filter(CartItem.cart_id == cart.id)
        .all()
    )

    assert items == []

    print("✓ Clear cart test passed")


# ==========================================
# Calculate Cart Total
# ==========================================

def test_calculate_total(
    db: Session,
):
    user, cart = create_cart(db)

    product_one = create_test_product(
        db,
        name="Jersey One",
        price=Decimal("50.00"),
    )

    product_two = create_test_product(
        db,
        name="Jersey Two",
        price=Decimal("25.50"),
    )

    CartService.add_item(
        db,
        cart,
        CartItemCreate(
            product_id=product_one.id,
            quantity=2,
        ),
    )

    CartService.add_item(
        db,
        cart,
        CartItemCreate(
            product_id=product_two.id,
            quantity=3,
        ),
    )

    db.refresh(cart)

    total = CartService.calculate_total(cart)

    expected_total = (
        Decimal("50.00") * 2
        + Decimal("25.50") * 3
    )

    assert total == expected_total
    assert total == Decimal("176.50")

    print("✓ Calculate cart total test passed")


# ==========================================
# Empty Cart Total
# ==========================================

def test_calculate_empty_cart_total(
    db: Session,
):
    user, cart = create_cart(db)

    db.refresh(cart)

    total = CartService.calculate_total(cart)

    assert total == Decimal("0.00")

    print("✓ Empty cart total test passed")


# ==========================================
# Cart Total Uses Current Product Price
# ==========================================

def test_calculate_total_uses_current_product_price(
    db: Session,
):
    user, cart = create_cart(db)

    product = create_test_product(
        db,
        price=Decimal("100.00"),
    )

    CartService.add_item(
        db,
        cart,
        CartItemCreate(
            product_id=product.id,
            quantity=2,
        ),
    )

    product.price = Decimal("80.00")
    db.commit()
    db.refresh(product)
    db.refresh(cart)

    total = CartService.calculate_total(cart)

    assert total == Decimal("160.00")

    print("✓ Current product price calculation test passed")