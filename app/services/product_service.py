from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate


class ProductService:
    """
    Handles product-related business logic and
    database operations.
    """

    # ==========================================
    # Create Product
    # ==========================================

    @staticmethod
    def create_product(
        db: Session,
        data: ProductCreate,
    ) -> Product:
        """
        Create and persist a new product.
        """

        product = Product(
            name=data.name,
            sport=data.sport,
            category=data.category,
            team=data.team,
            league=data.league,
            brand=data.brand,
            price=data.price,
            old_price=data.old_price,
            rating=data.rating,
            image=data.image,
            is_featured=data.is_featured,
            is_new=data.is_new,
            is_best_seller=data.is_best_seller,
            in_stock=data.in_stock,
        )

        db.add(product)
        db.commit()
        db.refresh(product)

        return product

    # ==========================================
    # Get Product By ID
    # ==========================================

    @staticmethod
    def get_product_by_id(
        db: Session,
        product_id: int,
    ) -> Product | None:
        """
        Retrieve a product by its primary key.
        """

        return (
            db.query(Product)
            .filter(Product.id == product_id)
            .first()
        )

    # ==========================================
    # Get All Products
    # ==========================================

    @staticmethod
    def get_products(
        db: Session,
    ) -> list[Product]:
        """
        Retrieve all products.
        """

        return (
            db.query(Product)
            .order_by(Product.id.desc())
            .all()
        )

    # ==========================================
    # Update Product
    # ==========================================

    @staticmethod
    def update_product(
        db: Session,
        product: Product,
        data: ProductUpdate,
    ) -> Product:
        """
        Update an existing product using only the
        fields supplied by the caller.
        """

        update_data = data.model_dump(
            exclude_unset=True
        )

        for field, value in update_data.items():
            setattr(product, field, value)

        db.commit()
        db.refresh(product)

        return product

    # ==========================================
    # Delete Product
    # ==========================================

    @staticmethod
    def delete_product(
        db: Session,
        product: Product,
    ) -> None:
        """
        Delete an existing product.
        """

        db.delete(product)
        db.commit()