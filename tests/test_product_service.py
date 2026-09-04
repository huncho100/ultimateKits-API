from decimal import Decimal

from app.schemas.product import ProductCreate, ProductUpdate
from app.services.product_service import ProductService


# ==========================================
# Test Product Data
# ==========================================

def create_product_data(
    name: str = "Manchester United Home Jersey",
) -> ProductCreate:
    """
    Return valid product data for testing.
    """

    return ProductCreate(
        name=name,
        sport="Football",
        category="Jerseys",
        team="Manchester United",
        league="Premier League",
        brand="Adidas",
        price=Decimal("89.99"),
        old_price=Decimal("109.99"),
        rating=4.5,
        image="/images/manchester-united-home.jpg",
        is_featured=True,
        is_new=True,
        is_best_seller=False,
        in_stock=True,
    )


# ==========================================
# Create Product
# ==========================================

def test_create_product(db):
    data = create_product_data()

    product = ProductService.create_product(
        db,
        data,
    )

    assert product.id is not None
    assert product.name == "Manchester United Home Jersey"
    assert product.sport == "Football"
    assert product.team == "Manchester United"
    assert product.price == Decimal("89.99")
    assert product.rating == 4.5
    assert product.is_featured is True
    assert product.is_new is True
    assert product.in_stock is True

    print("✓ Create product test passed")


# ==========================================
# Get Product By ID
# ==========================================

def test_get_product_by_id(db):
    data = create_product_data()

    created_product = ProductService.create_product(
        db,
        data,
    )

    product = ProductService.get_product_by_id(
        db,
        created_product.id,
    )

    assert product is not None
    assert product.id == created_product.id
    assert product.name == created_product.name

    print("✓ Get product by ID test passed")


# ==========================================
# Get Nonexistent Product
# ==========================================

def test_get_nonexistent_product(db):
    product = ProductService.get_product_by_id(
        db,
        999999,
    )

    assert product is None

    print("✓ Get nonexistent product test passed")


# ==========================================
# Get All Products
# ==========================================

def test_get_products(db):
    product_one = ProductService.create_product(
        db,
        create_product_data(
            "Manchester United Home Jersey"
        ),
    )

    product_two = ProductService.create_product(
        db,
        create_product_data(
            "Lakers White Jersey"
        ),
    )

    products = ProductService.get_products(db)

    product_ids = [product.id for product in products]

    assert product_one.id in product_ids
    assert product_two.id in product_ids
    assert len(products) >= 2

    print("✓ Get products test passed")


# ==========================================
# Update Product
# ==========================================

def test_update_product(db):
    product = ProductService.create_product(
        db,
        create_product_data(),
    )

    update_data = ProductUpdate(
        price=Decimal("79.99"),
        rating=4.8,
        in_stock=False,
    )

    updated_product = ProductService.update_product(
        db,
        product,
        update_data,
    )

    assert updated_product.price == Decimal("79.99")
    assert updated_product.rating == Decimal("4.80")
    assert updated_product.in_stock is False

    print("✓ Update product test passed")


# ==========================================
# Partial Product Update
# ==========================================

def test_partial_product_update(db):
    product = ProductService.create_product(
        db,
        create_product_data(),
    )

    original_name = product.name
    original_price = product.price

    update_data = ProductUpdate(
        is_featured=False,
    )

    updated_product = ProductService.update_product(
        db,
        product,
        update_data,
    )

    assert updated_product.is_featured is False
    assert updated_product.name == original_name
    assert updated_product.price == original_price

    print("✓ Partial product update test passed")


# ==========================================
# Delete Product
# ==========================================

def test_delete_product(db):
    product = ProductService.create_product(
        db,
        create_product_data(),
    )

    product_id = product.id

    ProductService.delete_product(
        db,
        product,
    )

    deleted_product = ProductService.get_product_by_id(
        db,
        product_id,
    )

    assert deleted_product is None

    print("✓ Delete product test passed")