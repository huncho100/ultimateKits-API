import csv
import runpy
from decimal import Decimal
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text

from app.core.config import settings
from app.database.development_catalog import (
    LEGACY_PRICES, NEW_PRODUCTS, require_development_database,
)
from app.database.seed import PRODUCTS, seed_development_catalog, seed_products
from app.models.product import Product
from app.models.product_image import ProductImage
from app.schemas.product import ProductUpdate
from app.services.product_service import ProductService
from scripts import reconcile_product_images


def snapshot(db):
    return {
        product.id: (
            product.name, product.price, product.old_price,
            product.development_placeholder, product.catalog_key,
            tuple(product.gallery), product.in_stock, product.stock_quantity,
        )
        for product in db.query(Product).all()
    }


def test_complete_development_catalog_and_filter_responses(db, client):
    original_ids = {product.name: product.id for product in db.query(Product).all()}
    result = seed_development_catalog(db)
    db.commit()

    assert result["products_created"] == len(NEW_PRODUCTS) == 36
    assert db.query(Product).count() == 51
    assert db.query(ProductImage).count() == 65
    for name, product_id in original_ids.items():
        assert db.get(Product, product_id).name == name
    for product in db.query(Product).all():
        assert Decimal("15000.00") <= product.price <= Decimal("35000.00")
        assert product.image == product.gallery[0]
        assert product.in_stock
        assert product.stock_quantity is None
        assert all(reconcile_product_images.image_exists(path) for path in product.gallery)
    assert db.query(Product).filter(Product.development_placeholder.is_(True)).count() == 45

    for filters, count in [
        ({}, 51),
        ({"sport": "Football"}, 37),
        ({"league": "National Team"}, 23),
        ({"category": "Retro"}, 7),
        ({"sport": "Basketball"}, 11),
        ({"sport": "Baseball"}, 3),
        ({"team": "Does not exist"}, 0),
    ]:
        response = client.get("/products", params=filters)
        assert response.status_code == 200
        assert len(response.json()) == count


def test_reseeding_preserves_ids_prices_status_and_gallery_ids(db):
    seed_development_catalog(db)
    db.commit()
    product = db.query(Product).filter(
        Product.name == NEW_PRODUCTS[0].name
    ).one()
    product.name = "Operator renamed Manchester City shirt"
    ProductService.update_product(
        db, product,
        ProductUpdate(price=Decimal("41000.00"), in_stock=False, stock_quantity=0),
    )
    before = snapshot(db)
    gallery_ids = {image.id for image in db.query(ProductImage).all()}

    first = seed_development_catalog(db)
    second = seed_development_catalog(db)
    seed_products(db)
    db.commit()

    assert first == second == {
        "products_created": 0, "prices_updated": 0, "gallery_images_created": 0,
    }
    assert snapshot(db) == before
    assert {image.id for image in db.query(ProductImage).all()} == gallery_ids
    assert not product.development_placeholder


def test_only_recognized_unclaimed_legacy_prices_are_replaced(db):
    club = db.query(Product).filter(Product.name == "Chelsea Home Jersey").one()
    club.catalog_key = None
    club.price, club.old_price = LEGACY_PRICES[club.name]
    club.development_placeholder = False
    approved = db.query(Product).filter(Product.name == "England Retro Jersey").one()
    approved_id = approved.id
    other = db.query(Product).filter(Product.name == "Arsenal Home Jersey").one()
    other.catalog_key = None
    other.price = Decimal("32000.00")
    other.old_price = None
    other.development_placeholder = False
    db.commit()

    result = seed_development_catalog(db)
    db.commit()

    assert result["prices_updated"] == 1
    assert club.price == Decimal("25000.00") and club.development_placeholder
    assert other.price == Decimal("32000.00") and not other.development_placeholder
    assert approved.id == approved_id
    assert approved.price == Decimal("25000.00")
    assert not approved.development_placeholder


def test_fixed_printing_and_alternate_views_are_not_duplicate_designs(db):
    seed_development_catalog(db)
    db.commit()
    germany = db.query(Product).filter(Product.name == "Germany Away Jersey").one()
    assert len(germany.gallery) == 2
    flame = db.query(Product).filter(Product.name == "Nigeria White/Green Flame Jersey").one()
    assert len(flame.gallery) == 3
    assert not any(path.endswith("/retro/nigeria-white.jpg") for path in flame.gallery)
    brazil = db.query(Product).filter(Product.team == "Brazil").all()
    assert {product.name for product in brazil} == {
        "Brazil Home Jersey", "Brazil Away Jersey", "Brazil Away Jersey - No. 7",
    }
    hashes = [
        reconcile_product_images.image_hash(
            reconcile_product_images.public_image_file(image.image_url)
        )
        for image in db.query(ProductImage).all()
    ]
    assert len(hashes) == len(set(hashes))


def test_ambiguous_identity_refuses_instead_of_duplicating(db):
    db.add(Product(
        name=NEW_PRODUCTS[0].name, sport="Football", category="Jerseys",
        price=Decimal("25000.00"),
    ))
    db.add(Product(
        name="A conflicting record", sport="Football", category="Jerseys",
        image=NEW_PRODUCTS[0].paths[0], price=Decimal("25000.00"),
    ))
    db.commit()
    with pytest.raises(ValueError, match="Ambiguous catalog identity"):
        seed_development_catalog(db)
    db.rollback()


@pytest.mark.parametrize(
    ("url", "debug"),
    [
        ("postgresql://user:password@remote.example/ultimatekits", True),
        ("postgresql://user:password@localhost/production", True),
        ("postgresql://user:password@localhost/ultimatekits", False),
    ],
)
def test_production_or_wrong_database_seed_is_refused(monkeypatch, url, debug):
    from sqlalchemy.engine import make_url
    from types import SimpleNamespace
    monkeypatch.setattr(settings, "DEBUG", debug)
    monkeypatch.setattr(settings, "DATABASE_URL", url)
    fake_db = SimpleNamespace(
        get_bind=lambda: SimpleNamespace(engine=SimpleNamespace(url=make_url(url)))
    )
    with pytest.raises(RuntimeError, match="Production seeding is refused"):
        require_development_database(fake_db)


def test_price_register_is_output_not_seed_input(db, monkeypatch, tmp_path):
    seed_development_catalog(db)
    db.commit()
    report = tmp_path / "prices.csv"
    monkeypatch.setattr(reconcile_product_images, "PRICE_REPORT_PATH", report)
    reconcile_product_images.write_price_register(db)
    with report.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 51
    placeholders = [row for row in rows if row["development_placeholder"] == "true"]
    assert len(placeholders) == 45
    assert all(row["product_id"] and row["catalog_key"] for row in rows)
    assert all(
        Decimal("15000.00") <= Decimal(row["temporary_ngn_price"]) <= Decimal("35000.00")
        for row in placeholders
    )
    before = snapshot(db)
    report.write_text("this is not seed input", encoding="utf-8")
    seed_development_catalog(db)
    db.commit()
    assert snapshot(db) == before


def test_admin_price_patch_clears_placeholder_but_other_edits_do_not(db, client):
    from tests.test_product_routes import create_admin_headers
    admin_headers = create_admin_headers(db)
    product = db.query(Product).filter(Product.development_placeholder.is_(True)).first()
    response = client.patch(
        f"/products/{product.id}", json={"in_stock": True}, headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["development_placeholder"] is True
    response = client.patch(
        f"/products/{product.id}", json={"price": "25000.00"}, headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["development_placeholder"] is False
    seed_development_catalog(db)
    seed_products(db)
    db.commit()
    assert product.price == Decimal("25000.00")
    assert not product.development_placeholder
    response = client.patch(
        f"/products/{product.id}", json={"price": None}, headers=admin_headers,
    )
    assert response.status_code == 422


def test_migration_adds_provenance_without_repricing_or_removing_data():
    path = Path(__file__).resolve().parents[1] / "alembic" / "versions" / (
        "b62f0d8e3c14_add_catalog_identity_and_development_price_flag.py"
    )
    migration = runpy.run_path(str(path))
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE products (id INTEGER PRIMARY KEY, price NUMERIC(10,2))"))
        connection.execute(text("INSERT INTO products VALUES (7, 31000)"))
        with Operations.context(MigrationContext.configure(connection)):
            migration["upgrade"]()
        row = connection.execute(text("SELECT * FROM products")).mappings().one()
        assert row["id"] == 7 and row["price"] == 31000
        assert not row["development_placeholder"]
        assert row["catalog_key"] is None
        assert inspect(connection).get_indexes("products")[0]["unique"] == 1
