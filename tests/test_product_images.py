import runpy
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, text

from app.database.seed import PRODUCTS


def test_seeded_product_image_paths_use_public_product_directory():
    images_by_name = {
        product["name"]: product["image"]
        for product in PRODUCTS
    }

    for product in PRODUCTS:
        image = product["image"]
        assert image is None or image.startswith(
            "/images/products/"
        )

    assert images_by_name["Real Madrid Home Jersey"] == (
        "/images/products/football/real-madrid-home2.jpg"
    )
    assert images_by_name["Liverpool Home Jersey"] == (
        "/images/products/football/liverpool-home.jpg"
    )
    assert images_by_name["Bayern Munich Home Jersey"] == (
        "/images/products/football/bayern-munich-home.jpg"
    )
    assert images_by_name["Inter Milan Home Jersey"] == (
        "/images/products/football/inter-milan-home.jpg"
    )
    assert images_by_name["Paris Saint-Germain Home Jersey"] == (
        "/images/products/football/psg-home.jpg"
    )
    assert images_by_name["Manchester United Home Jersey"] == (
        "/images/products/football/manchester-united-home.webp"
    )
    assert images_by_name["Chelsea Home Jersey"] == (
        "/images/products/football/chelsea-home.webp"
    )


def test_product_image_migration_repairs_and_clears_paths():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "e91f6a2c4b10_correct_product_image_paths.py"
    )
    upgrade = runpy.run_path(str(migration_path))["upgrade"]
    engine = create_engine("sqlite://")

    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE products "
                "(name VARCHAR(255), image VARCHAR(500))"
            )
        )
        connection.execute(
            text(
                "INSERT INTO products (name, image) "
                "VALUES (:name, :image)"
            ),
            [
                {
                    "name": "Real Madrid Home Jersey",
                    "image": "/images/real-madrid-home.jpg",
                },
                {
                    "name": "Liverpool Home Jersey",
                    "image": None,
                },
                {
                    "name": "Legacy Arsenal",
                    "image": "/images/arsenal-home.jpg",
                },
                {
                    "name": "Broken image",
                    "image": "/images/not-present.jpg",
                },
                {
                    "name": "Ambiguous legacy image",
                    "image": "/images/dallas-white.jpg",
                },
                {
                    "name": "Valid existing image",
                    "image": "/images/products/football/arsenal-home.jpg",
                },
            ],
        )

        with Operations.context(
            MigrationContext.configure(connection)
        ):
            upgrade()

        rows = dict(
            connection.execute(
                text("SELECT name, image FROM products")
            ).all()
        )

    assert rows == {
        "Real Madrid Home Jersey": (
            "/images/products/football/real-madrid-home2.jpg"
        ),
        "Liverpool Home Jersey": (
            "/images/products/football/liverpool-home.jpg"
        ),
        "Legacy Arsenal": (
            "/images/products/football/arsenal-home.jpg"
        ),
        "Broken image": None,
        "Ambiguous legacy image": None,
        "Valid existing image": (
            "/images/products/football/arsenal-home.jpg"
        ),
    }


def test_webp_migration_only_corrects_named_products_with_stale_jpg_paths():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "f24c8d6a901b_correct_club_webp_image_paths.py"
    )
    upgrade = runpy.run_path(str(migration_path))["upgrade"]
    rows = [
        (1, "Manchester United Home Jersey",
         "/images/products/football/manchester-united-home.jpg", "89.99"),
        (2, "Chelsea Home Jersey", "/images/chelsea-home.jpg", "91.00"),
        (3, "Chelsea Home Jersey",
         "/images/products/football/chelsea-home2.webp", "80.00"),
        (4, "Other product",
         "/images/products/football/manchester-united-home.jpg", "70.00"),
        (5, "Chelsea Home Jersey", None, "60.00"),
    ]
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text(
            "CREATE TABLE products "
            "(id INTEGER, name VARCHAR(255), image VARCHAR(500), price TEXT)"
        ))
        connection.execute(
            text("INSERT INTO products VALUES (:id, :name, :image, :price)"),
            [
                dict(zip(("id", "name", "image", "price"), row))
                for row in rows
            ],
        )
        with Operations.context(MigrationContext.configure(connection)):
            upgrade()
            upgrade()
        after = connection.execute(
            text("SELECT id, name, image, price FROM products ORDER BY id")
        ).all()

    expected = list(rows)
    expected[0] = (
        1, rows[0][1],
        "/images/products/football/manchester-united-home.webp", "89.99",
    )
    expected[1] = (
        2, rows[1][1], "/images/products/football/chelsea-home.webp", "91.00",
    )
    assert after == expected
