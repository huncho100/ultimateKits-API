import runpy
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, text

from app.database.seed import PRODUCTS, PRODUCT_GALLERY_IMAGES


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
        "/images/products/football/chelsea-home-front.webp"
    )
    assert images_by_name["FC Barcelona Retro Jersey"] == (
        "/images/products/retro/barca-retro.jpg"
    )
    assert images_by_name["England Retro Jersey"] == (
        "/images/products/retro/england-retro.jpg"
    )
    assert images_by_name["Inter Milan Retro Jersey"] == (
        "/images/products/retro/inter-retro.jpg"
    )
    assert images_by_name["Liverpool Retro Jersey"] == (
        "/images/products/retro/liverpool-retro.jpg"
    )
    assert images_by_name["Nigeria Retro Jersey — Green Patterned"] == (
        "/images/products/retro/nigeria-retro-green.jpg"
    )
    assert images_by_name["Nigeria Retro Jersey — White"] == (
        "/images/products/retro/nigeria-retro-white.jpg"
    )

    frontend_public = (
        Path(__file__).resolve().parents[2]
        / "ultimateKits-FE"
        / "public"
    )
    all_seed_paths = [
        product["image"]
        for product in PRODUCTS
        if product["image"]
    ]
    all_seed_paths.extend(
        image_path
        for paths in PRODUCT_GALLERY_IMAGES.values()
        for image_path in paths
    )
    for image_path in all_seed_paths:
        assert (frontend_public / image_path.lstrip("/")).is_file(), (
            image_path
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


def test_gallery_migration_corrects_chelsea_path_and_backfills_primary_images():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "a52c7e9d4b61_add_product_image_gallery.py"
    )
    upgrade = runpy.run_path(str(migration_path))["upgrade"]
    engine = create_engine("sqlite://")

    with engine.begin() as connection:
        connection.execute(text(
            "CREATE TABLE products "
            "(id INTEGER PRIMARY KEY, name VARCHAR(255), image VARCHAR(500))"
        ))
        connection.execute(
            text("INSERT INTO products VALUES (:id, :name, :image)"),
            [
                {
                    "id": 1,
                    "name": "Chelsea Home Jersey",
                    "image": "/images/products/football/chelsea-home.webp",
                },
                {
                    "id": 2,
                    "name": "No image product",
                    "image": None,
                },
            ],
        )

        with Operations.context(MigrationContext.configure(connection)):
            upgrade()

        images = connection.execute(text(
            "SELECT product_id, image_url, sort_order, is_primary "
            "FROM product_images ORDER BY product_id"
        )).all()
        chelsea_path = connection.execute(text(
            "SELECT image FROM products WHERE id = 1"
        )).scalar_one()

    assert chelsea_path == (
        "/images/products/football/chelsea-home-front.webp"
    )
    assert images == [
        (
            1,
            "/images/products/football/chelsea-home-front.webp",
            0,
            1,
        )
    ]
