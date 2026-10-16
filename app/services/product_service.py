from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.models.product import Product
from app.models.product_image import ProductImage
from app.schemas.product import ProductCreate, ProductUpdate


class ProductService:
    """
    Handles product-related business logic and
    database operations.
    """

    @staticmethod
    def _replace_gallery(
        db: Session,
        product: Product,
        image_paths: list[str],
    ) -> None:
        unique_paths = list(dict.fromkeys(image_paths))
        if product.id is not None:
            product.product_images.clear()
            db.flush()
        else:
            product.product_images.clear()

        product.image = unique_paths[0] if unique_paths else None
        product.product_images = [
            ProductImage(
                image_url=image_path,
                sort_order=index,
                is_primary=index == 0,
            )
            for index, image_path in enumerate(unique_paths)
        ]

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
            description=data.description,
            price=data.price,
            old_price=data.old_price,
            rating=data.rating,
            image=data.image,
            is_featured=data.is_featured,
            is_new=data.is_new,
            is_best_seller=data.is_best_seller,
            in_stock=data.in_stock,
            stock_quantity=data.stock_quantity,
        )

        image_paths = list(data.gallery)
        if data.image:
            image_paths = [data.image] + [
                path for path in image_paths if path != data.image
            ]
        ProductService._replace_gallery(db, product, image_paths)

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
            .options(selectinload(Product.product_images))
            .filter(Product.id == product_id)
            .first()
        )

    # ==========================================
    # Get All Products
    # ==========================================

    @staticmethod
    def get_products(
        db: Session,
        *,
        sport: str | None = None,
        category: str | None = None,
        team: str | None = None,
        league: str | None = None,
    ) -> list[Product]:
        """
        Retrieve the complete catalog or exact metadata matches.
        """

        query = db.query(Product).options(
            selectinload(Product.product_images)
        )
        for column, value in (
            (Product.sport, sport),
            (Product.category, category),
            (Product.team, team),
            (Product.league, league),
        ):
            if value is not None:
                query = query.filter(
                    func.lower(func.trim(column)) == value.strip().lower()
                )

        return query.order_by(Product.id.desc()).all()

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
        if "price" in update_data:
            product.development_placeholder = False
        gallery_was_supplied = "gallery" in update_data
        image_was_supplied = "image" in update_data
        gallery_value = update_data.pop("gallery", None)
        image_value = update_data.get("image")

        for field, value in update_data.items():
            setattr(product, field, value)

        if gallery_was_supplied:
            paths = list(gallery_value or [])
            if image_was_supplied and image_value:
                paths = [image_value] + [
                    path for path in paths if path != image_value
                ]
            ProductService._replace_gallery(db, product, paths)
        elif image_was_supplied:
            if image_value is None:
                ProductService._replace_gallery(db, product, [])
            else:
                existing_paths = list(product.gallery)
                paths = [image_value]
                paths.extend(
                    path
                    for path in existing_paths
                    if path != image_value
                )
                ProductService._replace_gallery(db, product, paths)

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