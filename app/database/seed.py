from decimal import Decimal

from sqlalchemy.orm import Session

from app.database.database import SessionLocal

# ==========================================
# Register All SQLAlchemy Models
# ==========================================

from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.product import Product
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

PRODUCTS = [
    {
        "name": "Manchester United Home Jersey",
        "sport": "Football",
        "category": "Jerseys",
        "team": "Manchester United",
        "league": "Premier League",
        "brand": "Adidas",
        "price": Decimal("89.99"),
        "old_price": Decimal("109.99"),
        "rating": Decimal("4.50"),
        "image": "/images/manchester-united-home.jpg",
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
        "price": Decimal("89.99"),
        "old_price": Decimal("109.99"),
        "rating": Decimal("4.80"),
        "image": "/images/real-madrid-home.jpg",
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
        "price": Decimal("84.99"),
        "old_price": Decimal("99.99"),
        "rating": Decimal("4.60"),
        "image": "/images/arsenal-home.jpg",
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
        "price": Decimal("89.99"),
        "old_price": None,
        "rating": Decimal("4.70"),
        "image": "/images/barcelona-home.jpg",
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
        "price": Decimal("89.99"),
        "old_price": Decimal("109.99"),
        "rating": Decimal("4.40"),
        "image": "/images/liverpool-home.jpg",
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
        "price": Decimal("84.99"),
        "old_price": None,
        "rating": Decimal("4.50"),
        "image": "/images/bayern-munich-home.jpg",
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
        "price": Decimal("79.99"),
        "old_price": Decimal("99.99"),
        "rating": Decimal("4.30"),
        "image": "/images/inter-milan-home.jpg",
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
        "price": Decimal("89.99"),
        "old_price": None,
        "rating": Decimal("4.60"),
        "image": "/images/psg-home.jpg",
        "is_featured": True,
        "is_new": True,
        "is_best_seller": False,
        "in_stock": True,
    },
]


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
) -> None:
    """
    Create sample products if they do not
    already exist.
    """

    for product_data in PRODUCTS:
        existing_product = (
            db.query(Product)
            .filter(
                Product.name
                == product_data["name"]
            )
            .first()
        )

        if existing_product is None:
            product = Product(
                **product_data
            )

            db.add(product)

            print(
                f"Created product: "
                f"{product_data['name']}"
            )
        else:
            print(
                f"Product already exists: "
                f"{product_data['name']}"
            )


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