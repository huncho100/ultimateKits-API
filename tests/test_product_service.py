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
        image="/images/products/football/manchester-united-home.webp",
        is_featured=True,
        is_new=True,
        is_best_seller=False,
        in_stock=True,
        gallery=[
            "/images/products/football/manchester-united-home.webp",
            "/images/products/football/manchester-united-home-close-up.webp",
        ],
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
    assert product.gallery == [
        "/images/products/football/manchester-united-home.webp",
        "/images/products/football/manchester-united-home-close-up.webp",
    ]

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


def test_update_product_gallery_replaces_entries_and_primary(db):
    product = ProductService.create_product(
        db,
        create_product_data(),
    )
    new_primary = "/images/products/football/arsenal-home.jpg"
    new_alternate = "/images/products/football/liverpool-home.jpg"

    updated = ProductService.update_product(
        db,
        product,
        ProductUpdate(gallery=[new_primary, new_alternate]),
    )

    assert updated.image == new_primary
    assert updated.gallery == [new_primary, new_alternate]


def test_update_product_primary_preserves_alternate_images(db):
    product = ProductService.create_product(
        db,
        create_product_data(),
    )
    new_primary = "/images/products/football/arsenal-home.jpg"

    updated = ProductService.update_product(
        db,
        product,
        ProductUpdate(image=new_primary),
    )

    assert updated.gallery == [
        new_primary,
        "/images/products/football/manchester-united-home.webp",
        "/images/products/football/manchester-united-home-close-up.webp",
    ]


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

# ==========================================
# Product Description
# ==========================================

def test_create_product_without_description(db):
    """
    A product created without a description is stored
    with NULL, not with generated text.
    """

    product = ProductService.create_product(
        db,
        create_product_data(),
    )

    assert product.description is None


def test_create_product_with_description(db):
    """
    The create path passes description through to the
    model. ProductService.create_product builds Product
    from an explicit keyword list, so a field missing
    from that list would be silently dropped here.
    """

    data = ProductCreate(
        name="Arsenal Home Jersey",
        sport="Football",
        category="Jerseys",
        price=Decimal("84.99"),
        description="Official home shirt.",
    )

    product = ProductService.create_product(
        db,
        data,
    )

    assert product.description == "Official home shirt."


def test_update_product_sets_description(db):
    product = ProductService.create_product(
        db,
        create_product_data(),
    )

    assert product.description is None

    updated = ProductService.update_product(
        db,
        product,
        ProductUpdate(
            description="Now with a description.",
        ),
    )

    assert updated.description == (
        "Now with a description."
    )


def test_update_product_preserves_description(db):
    """
    An unrelated update must leave a published
    description alone.
    """

    product = ProductService.create_product(
        db,
        ProductCreate(
            name="Liverpool Home Jersey",
            sport="Football",
            category="Jerseys",
            price=Decimal("89.99"),
            description="Official home shirt.",
        ),
    )

    updated = ProductService.update_product(
        db,
        product,
        ProductUpdate(price=Decimal("79.99")),
    )

    assert updated.price == Decimal("79.99")
    assert updated.description == "Official home shirt."


def test_update_product_clears_description(db):
    """
    Sending null withdraws a published description and
    returns the product to the empty state.
    """

    product = ProductService.create_product(
        db,
        ProductCreate(
            name="Chelsea Home Jersey",
            sport="Football",
            category="Jerseys",
            price=Decimal("89.99"),
            description="Official home shirt.",
        ),
    )

    updated = ProductService.update_product(
        db,
        product,
        ProductUpdate(description=None),
    )

    assert updated.description is None


def test_update_description_leaves_other_fields_alone(db):
    """
    Publishing a description must not disturb price,
    stock, category, or image.
    """

    product = ProductService.create_product(
        db,
        create_product_data(),
    )

    before = (
        product.price,
        product.old_price,
        product.category,
        product.image,
        product.in_stock,
        product.stock_quantity,
        product.rating,
    )

    updated = ProductService.update_product(
        db,
        product,
        ProductUpdate(description="A description."),
    )

    assert (
        updated.price,
        updated.old_price,
        updated.category,
        updated.image,
        updated.in_stock,
        updated.stock_quantity,
        updated.rating,
    ) == before
