from decimal import Decimal

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database.database import SessionLocal
from app.database.development_catalog import (
    LEGACY_PRICES,
    NEW_PRODUCTS,
    catalog_key,
    require_development_database,
)

# ==========================================
# Register All SQLAlchemy Models
# ==========================================

from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.payment import Payment
from app.models.product import Product
from app.models.product_image import ProductImage
from app.models.user import User

from app.utils.security import hash_password


# ==========================================
# Seed User Configuration
# ==========================================

ADMIN_EMAIL = "admin@ultimatekits.com"
ADMIN_PASSWORD = "AdminPassword123!"

CUSTOMER_EMAIL = "customer@ultimatekits.com"
CUSTOMER_PASSWORD = "CustomerPassword123!"


# ==========================================
# Seed Products
# ==========================================
#
# `image` is a root-relative URL served by the
# frontend out of ultimateKits-FE/public, so
# "/images/products/football/arsenal-home.jpg" is the
# file at public/images/products/football/arsenal-home.jpg.
#
# Existing databases may still contain the former
# "/images/<file>.jpg" paths. The product-image Alembic
# migration moves those to the public directory paths,
# attaches the supplied club photos, and clears paths
# that do not resolve to a public image. See
# docs/product-images.md.

PRODUCTS = [
    {
        "name": "Manchester United Home Jersey",
        "sport": "Football",
        "category": "Jerseys",
        "team": "Manchester United",
        "league": "Premier League",
        "brand": "Adidas",
        "price": Decimal("25000.00"),
        "old_price": None,
        "rating": Decimal("4.50"),
        "image": "/images/products/football/manchester-united-home.webp",
        "is_featured": True,
        "is_new": True,
        "is_best_seller": True,
        "in_stock": True,
    },
    {
        "name": "Real Madrid Home Jersey",
        "sport": "Football",
        "category": "Jerseys",
        "team": "Real Madrid",
        "league": "La Liga",
        "brand": "Adidas",
        "price": Decimal("25000.00"),
        "old_price": None,
        "rating": Decimal("4.80"),
        "image": "/images/products/football/real-madrid-home2.jpg",
        "is_featured": True,
        "is_new": True,
        "is_best_seller": True,
        "in_stock": True,
    },
    {
        "name": "Arsenal Home Jersey",
        "sport": "Football",
        "category": "Jerseys",
        "team": "Arsenal",
        "league": "Premier League",
        "brand": "Adidas",
        "price": Decimal("25000.00"),
        "old_price": None,
        "rating": Decimal("4.60"),
        "image": "/images/products/football/arsenal-home.jpg",
        "is_featured": True,
        "is_new": False,
        "is_best_seller": True,
        "in_stock": True,
    },
    {
        "name": "FC Barcelona Home Jersey",
        "sport": "Football",
        "category": "Jerseys",
        "team": "FC Barcelona",
        "league": "La Liga",
        "brand": "Nike",
        "price": Decimal("25000.00"),
        "old_price": None,
        "rating": Decimal("4.70"),
        "image": "/images/products/football/barcelona-home.jpg",
        "is_featured": True,
        "is_new": True,
        "is_best_seller": False,
        "in_stock": True,
    },
    {
        "name": "Liverpool Home Jersey",
        "sport": "Football",
        "category": "Jerseys",
        "team": "Liverpool",
        "league": "Premier League",
        "brand": "Adidas",
        "price": Decimal("25000.00"),
        "old_price": None,
        "rating": Decimal("4.40"),
        "image": "/images/products/football/liverpool-home.jpg",
        "is_featured": False,
        "is_new": True,
        "is_best_seller": True,
        "in_stock": True,
    },
    {
        "name": "Bayern Munich Home Jersey",
        "sport": "Football",
        "category": "Jerseys",
        "team": "Bayern Munich",
        "league": "Bundesliga",
        "brand": "Adidas",
        "price": Decimal("25000.00"),
        "old_price": None,
        "rating": Decimal("4.50"),
        "image": "/images/products/football/bayern-munich-home.jpg",
        "is_featured": False,
        "is_new": False,
        "is_best_seller": True,
        "in_stock": True,
    },
    {
        "name": "Inter Milan Home Jersey",
        "sport": "Football",
        "category": "Jerseys",
        "team": "Inter Milan",
        "league": "Serie A",
        "brand": "Nike",
        "price": Decimal("25000.00"),
        "old_price": None,
        "rating": Decimal("4.30"),
        "image": "/images/products/football/inter-milan-home.jpg",
        "is_featured": False,
        "is_new": False,
        "is_best_seller": False,
        "in_stock": True,
    },
    {
        "name": "Paris Saint-Germain Home Jersey",
        "sport": "Football",
        "category": "Jerseys",
        "team": "Paris Saint-Germain",
        "league": "Ligue 1",
        "brand": "Nike",
        "price": Decimal("25000.00"),
        "old_price": None,
        "rating": Decimal("4.60"),
        "image": "/images/products/football/psg-home.jpg",
        "is_featured": True,
        "is_new": True,
        "is_best_seller": False,
        "in_stock": True,
    },
    {
        "name": "Chelsea Home Jersey",
        "sport": "Football",
        "category": "Jerseys",
        "team": "Chelsea",
        "league": "Premier League",
        "brand": "Nike",
        "price": Decimal("25000.00"),
        "old_price": None,
        "rating": Decimal("4.60"),
        "image": "/images/products/football/chelsea-home-front.webp",
        "is_featured": True,
        "is_new": True,
        "is_best_seller": False,
        "in_stock": True,
    },
    {
        "name": "FC Barcelona Retro Jersey",
        "sport": "Football",
        "category": "Retro",
        "team": "FC Barcelona",
        "league": None,
        "price": Decimal("25000.00"),
        "image": "/images/products/retro/barca-retro.jpg",
    },
    {
        "name": "England Retro Jersey",
        "sport": "Football",
        "category": "Retro",
        "team": "England",
        "league": "National Team",
        "price": Decimal("25000.00"),
        "image": "/images/products/retro/england-retro.jpg",
    },
    {
        "name": "Inter Milan Retro Jersey",
        "sport": "Football",
        "category": "Retro",
        "team": "Inter Milan",
        "league": None,
        "price": Decimal("25000.00"),
        "image": "/images/products/retro/inter-retro.jpg",
    },
    {
        "name": "Liverpool Retro Jersey",
        "sport": "Football",
        "category": "Retro",
        "team": "Liverpool",
        "league": None,
        "price": Decimal("25000.00"),
        "image": "/images/products/retro/liverpool-retro.jpg",
    },
    {
        "name": "Nigeria Retro Jersey — Green Patterned",
        "sport": "Football",
        "category": "Retro",
        "team": "Nigeria",
        "league": "National Team",
        "price": Decimal("25000.00"),
        "image": "/images/products/retro/nigeria-retro-green.jpg",
    },
    {
        "name": "Nigeria Retro Jersey — White",
        "sport": "Football",
        "category": "Retro",
        "team": "Nigeria",
        "league": "National Team",
        "price": Decimal("25000.00"),
        "image": "/images/products/retro/nigeria-retro-white.jpg",
    },
]

PRODUCT_GALLERY_IMAGES = {
    "Manchester United Home Jersey": [
        "/images/products/football/manchester-united-home-close-up.webp",
        "/images/products/football/manchester-united-home-model.webp",
        "/images/products/football/manchester-united-home-front.webp",
        "/images/products/football/manchester-united-home-33.jpg",
    ],
    "Chelsea Home Jersey": [
        "/images/products/football/chelsea-home-back.webp",
        "/images/products/football/chelsea-home-detail.webp",
    ],
    "Liverpool Home Jersey": [
        "/images/products/football/liverpool-home-close-up.jpg",
        "/images/products/football/liverpool-home-close-up2.jpg",
    ],
}


# ==========================================
# Seed Users
# ==========================================

def seed_users(
    db: Session,
) -> None:
    """
    Create default administrator and customer
    accounts if they do not already exist.
    """

    admin = (
        db.query(User)
        .filter(User.email == ADMIN_EMAIL)
        .first()
    )

    if admin is None:
        admin = User(
            first_name="Ultimate",
            last_name="Admin",
            email=ADMIN_EMAIL,
            password_hash=hash_password(
                ADMIN_PASSWORD
            ),
            role="admin",
            is_active=True,
        )

        db.add(admin)

        print(
            f"Created admin user: {ADMIN_EMAIL}"
        )
    else:
        print(
            f"Admin user already exists: "
            f"{ADMIN_EMAIL}"
        )

    customer = (
        db.query(User)
        .filter(User.email == CUSTOMER_EMAIL)
        .first()
    )

    if customer is None:
        customer = User(
            first_name="Sample",
            last_name="Customer",
            email=CUSTOMER_EMAIL,
            password_hash=hash_password(
                CUSTOMER_PASSWORD
            ),
            role="customer",
            is_active=True,
        )

        db.add(customer)

        print(
            f"Created customer user: "
            f"{CUSTOMER_EMAIL}"
        )
    else:
        print(
            f"Customer user already exists: "
            f"{CUSTOMER_EMAIL}"
        )


# ==========================================
# Seed Products
# ==========================================

def seed_products(
    db: Session,
) -> dict[str, int]:
    """
    Create sample products if they do not
    already exist.
    """

    require_development_database(db)
    created_products = 0
    for product_data in PRODUCTS:
        existing_product = find_catalog_product(
            db, product_data["name"], product_data["image"]
        )

        if existing_product is None:
            values = dict(product_data)
            values["catalog_key"] = catalog_key(product_data["name"])
            values["development_placeholder"] = product_data["name"] in LEGACY_PRICES
            product = Product(
                **values
            )

            db.add(product)
            db.flush()
            created_products += 1

            print(
                f"Created product: "
                f"{product_data['name']}"
            )
        else:
            print(
                f"Product already exists: "
                f"{product_data['name']}"
            )

    created_images = seed_product_images(db)
    print(
        "Product reconciliation: "
        f"{created_products} products created, "
        f"{created_images} gallery images associated."
    )
    return {
        "products_created": created_products,
        "gallery_images_created": created_images,
    }


def find_catalog_product(db: Session, name: str, image: str) -> Product | None:
    key = catalog_key(name)
    matches = db.query(Product).filter(or_(
        Product.catalog_key == key,
        Product.name == name,
        Product.image == image,
    )).all()
    if len(matches) > 1:
        raise ValueError(f"Ambiguous catalog identity for {key}; refusing duplicate seeding.")
    if matches and matches[0].catalog_key not in {None, key}:
        raise ValueError(f"Conflicting catalog identity for {key}.")
    return matches[0] if matches else None


def seed_development_catalog(db: Session) -> dict[str, int]:
    """Insert reviewed designs and replace only recognized, unclaimed legacy samples."""
    require_development_database(db)
    summary = {"products_created": 0, "prices_updated": 0, "gallery_images_created": 0}
    entries = [
        {
            **data,
            "catalog_key": catalog_key(data["name"]),
            "development_placeholder": data["name"] in LEGACY_PRICES,
        }
        for data in PRODUCTS
    ]
    entries.extend({
        "name": entry.name,
        "catalog_key": entry.key,
        "sport": entry.sport,
        "category": entry.category,
        "team": entry.team,
        "league": entry.league,
        "image": entry.paths[0],
        "price": entry.price,
        "development_placeholder": True,
        "in_stock": True,
        "stock_quantity": None,
    } for entry in NEW_PRODUCTS)

    for data in entries:
        product = find_catalog_product(db, data["name"], data["image"])
        if product is None:
            product = Product(**data)
            db.add(product)
            db.flush()
            summary["products_created"] += 1
        else:
            legacy_price = LEGACY_PRICES.get(data["name"])
            if (
                product.catalog_key is None
                and legacy_price == (product.price, product.old_price)
                and product.image == data["image"]
            ):
                product.price = data["price"]
                product.old_price = None
                product.development_placeholder = True
                summary["prices_updated"] += 1
            product.catalog_key = data["catalog_key"]

    summary["gallery_images_created"] = seed_product_images(db)
    db.flush()
    return summary


def seed_product_images(db: Session) -> int:
    """Associate known primary and alternate images once."""
    created_images = 0

    alternates = {
        **{
            catalog_key(name): paths
            for name, paths in PRODUCT_GALLERY_IMAGES.items()
        },
        **{
            entry.key: entry.paths[1:]
            for entry in NEW_PRODUCTS
        },
    }
    for product in db.query(Product).all():
        paths = ([product.image] if product.image else [])
        paths.extend(alternates.get(
            product.catalog_key or catalog_key(product.name), []
        ))
        paths = list(dict.fromkeys(paths))
        existing = {
            image.image_url: image
            for image in product.product_images
        }
        # Demote stale primary rows before promotion to satisfy the unique index.
        for image in existing.values():
            image.is_primary = False
        db.flush()

        for index, image_path in enumerate(paths):
            image = existing.get(image_path)
            if image is None:
                image = ProductImage(
                    product_id=product.id,
                    image_url=image_path,
                )
                product.product_images.append(image)
                created_images += 1

            image.sort_order = index
            image.is_primary = image_path == product.image

        db.flush()

    return created_images


# ==========================================
# Seed Database
# ==========================================

def seed_database() -> None:
    """
    Seed the Ultimate Kits database with
    default users and sample products.
    """

    db = SessionLocal()

    try:
        require_development_database(db)
        seed_users(db)
        seed_products(db)

        db.commit()

        print(
            "\nDatabase seeding completed successfully."
        )

    except Exception:
        db.rollback()

        print(
            "\nDatabase seeding failed. "
            "Changes have been rolled back."
        )

        raise

    finally:
        db.close()


# ==========================================
# Script Entry Point
# ==========================================

if __name__ == "__main__":
    seed_database()