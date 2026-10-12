from decimal import Decimal

import pytest

from app.database.seed import PRODUCTS, seed_products
from app.models.product import Product


@pytest.fixture
def collection_products(db):
    products = [
        Product(
            name="Test national jersey",
            sport=" Football ",
            category="Jerseys",
            team=" Test Country ",
            league=" National Team ",
            price=Decimal("50.00"),
            in_stock=False,
        ),
        Product(
            name="Test retro jersey",
            sport="Football",
            category=" Retro ",
            team="Test Club",
            league=None,
            price=Decimal("60.00"),
        ),
        Product(
            name="Test basketball jersey",
            sport="Basketball",
            category="Jerseys",
            team=None,
            league=None,
            price=Decimal("70.00"),
        ),
    ]
    db.add_all(products)
    db.commit()
    return products


def test_unfiltered_catalog_returns_every_record(client, db, collection_products):
    expected_ids = [
        product.id
        for product in db.query(Product).order_by(Product.id.desc()).all()
    ]
    response = client.get("/products")

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert [product["id"] for product in response.json()] == expected_ids
    national = next(
        product for product in response.json()
        if product["id"] == collection_products[0].id
    )
    assert national["sport"] == " Football "
    assert national["category"] == "Jerseys"
    assert national["team"] == " Test Country "
    assert national["league"] == " National Team "
    assert national["price"] == "50.00"
    assert national["in_stock"] is False


@pytest.mark.parametrize(
    ("params", "index"),
    [
        ({"league": "National Team", "team": "test country"}, 0),
        (
            {
                "sport": " football ",
                "league": " NATIONAL TEAM ",
                "team": "test country",
            },
            0,
        ),
        ({"category": "retro", "team": "test club"}, 1),
        (
            {
                "sport": "Football",
                "category": " Retro ",
                "team": "test club",
            },
            1,
        ),
        ({"team": "test country"}, 0),
        ({"sport": "basketball"}, 2),
    ],
)
def test_metadata_filters_match_collections(
    client, collection_products, params, index,
):
    response = client.get("/products", params=params)

    assert response.status_code == 200
    assert [product["id"] for product in response.json()] == [
        collection_products[index].id
    ]


@pytest.mark.parametrize(
    "params",
    [
        {"sport": "National Teams"},
        {"sport": "Retro"},
        {"sport": "Basketball", "category": "Retro"},
        {"team": "Not in catalog"},
    ],
)
def test_filters_without_matches_return_empty_array(
    client, collection_products, params,
):
    response = client.get("/products", params=params)

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.parametrize("field", ["sport", "category", "team", "league"])
@pytest.mark.parametrize("value", ["", "   "])
def test_blank_filters_are_rejected(client, field, value):
    assert client.get("/products", params={field: value}).status_code == 422


def test_existing_football_filter_returns_all_seeded_products(client, db):
    expected_ids = [
        product.id
        for product in db.query(Product)
        .filter(Product.category == "Jerseys", Product.sport == "Football")
        .order_by(Product.id.desc())
        .all()
    ]
    assert len(expected_ids) == 9
    response = client.get(
        "/products",
        params={"sport": "Football", "category": "Jerseys"},
    )

    assert response.status_code == 200
    assert [product["id"] for product in response.json()] == expected_ids
    assert all(
        product["category"] == "Jerseys" and product["sport"] == "Football"
        for product in response.json()
    )


def test_approved_retro_seed_metadata_and_collection_filters(client, db):
    retro = client.get(
        "/products",
        params={"sport": "Football", "category": "Retro"},
    )
    assert retro.status_code == 200
    assert len(retro.json()) == 6

    national_teams = client.get(
        "/products",
        params={"sport": "Football", "league": "National Team"},
    )
    assert national_teams.status_code == 200
    assert {
        (product["name"], product["category"])
        for product in national_teams.json()
    } == {
        ("England Retro Jersey", "Retro"),
        ("Nigeria Retro Jersey — Green Patterned", "Retro"),
        ("Nigeria Retro Jersey — White", "Retro"),
    }

    assert {
        product["name"]
        for product in retro.json()
    } == {
        "FC Barcelona Retro Jersey",
        "England Retro Jersey",
        "Inter Milan Retro Jersey",
        "Liverpool Retro Jersey",
        "Nigeria Retro Jersey — Green Patterned",
        "Nigeria Retro Jersey — White",
    }

    for product in retro.json():
        assert product["price"] == "25000.00"
        assert product["sport"] == "Football"
        assert product["rating"] == 0.0
        assert product["old_price"] is None
        assert product["stock_quantity"] is None
        assert product["brand"] is None
        assert product["in_stock"] is True


def test_repeated_seed_preserves_existing_catalog(db, collection_products):
    existing = db.query(Product).order_by(Product.id).first()
    existing.price = Decimal("123.45")
    db.commit()
    before = {
        product.id: (product.name, product.price, product.sport, product.category)
        for product in db.query(Product).all()
    }

    seed_products(db)
    seed_products(db)
    db.commit()

    after = {
        product.id: (product.name, product.price, product.sport, product.category)
        for product in db.query(Product).all()
    }
    assert after == before


def test_seed_adds_missing_chelsea_once_without_overwriting_existing(db):
    chelsea = db.query(Product).filter(
        Product.name == "Chelsea Home Jersey"
    ).one()
    db.delete(chelsea)
    db.commit()
    before = {
        product.id: (product.name, product.price, product.image)
        for product in db.query(Product).all()
    }

    seed_products(db)
    seed_products(db)
    db.commit()

    chelsea = db.query(Product).filter(
        Product.name == "Chelsea Home Jersey"
    ).one()
    assert chelsea.image == "/images/products/football/chelsea-home.webp"
    assert chelsea.price == next(
        product["price"] for product in PRODUCTS
        if product["name"] == "Chelsea Home Jersey"
    )
    assert db.query(Product).count() == len(before) + 1
    assert {
        product.id: (product.name, product.price, product.image)
        for product in db.query(Product).filter(Product.id.in_(before)).all()
    } == before


def test_repeated_seed_adds_each_approved_retro_product_once(db):
    approved_names = {
        product["name"]
        for product in PRODUCTS
        if product["category"] == "Retro"
    }
    before_count = db.query(Product).count()

    seed_products(db)
    seed_products(db)
    db.commit()

    seeded = db.query(Product).filter(
        Product.name.in_(approved_names)
    ).all()
    assert len(seeded) == 6
    assert db.query(Product).count() == before_count
    assert {product.name for product in seeded} == approved_names
