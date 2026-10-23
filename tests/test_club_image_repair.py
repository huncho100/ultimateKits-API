import pytest
import sqlalchemy as sa
from sqlalchemy.engine import make_url

from scripts.repair_club_image_paths import (
    FRONTEND_PUBLIC,
    IMAGE_REPAIRS,
    PREFIX,
    repair_image_paths,
    require_local_development_database,
)


@pytest.mark.parametrize("with_gallery", [False, True])
def test_repair_is_idempotent_and_preserves_other_data(tmp_path, with_gallery):
    for _, _, filename in IMAGE_REPAIRS:
        path = tmp_path / (PREFIX + filename).lstrip("/")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()

    engine = sa.create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(sa.text(
            "CREATE TABLE products "
            "(id INTEGER PRIMARY KEY, name TEXT, image TEXT, price TEXT, "
            "stock_quantity INTEGER)"
        ))
        rows = [
            {"id": i, "name": name, "image": PREFIX + old,
             "price": "25000.00", "stock_quantity": 7}
            for i, (name, old, _) in enumerate(IMAGE_REPAIRS, 1)
        ]
        rows.extend([
            {"id": 10, "name": "Chelsea Home Jersey",
             "image": PREFIX + "chelsea-home-back.webp",
             "price": "99.00", "stock_quantity": 2},
            {"id": 11, "name": "Unrelated product",
             "image": PREFIX + "chelsea-home-front.webp",
             "price": "80.00", "stock_quantity": 0},
            {"id": 12, "name": "Chelsea Home Jersey", "image": None,
             "price": "70.00", "stock_quantity": 3},
        ])
        connection.execute(sa.text(
            "INSERT INTO products VALUES "
            "(:id, :name, :image, :price, :stock_quantity)"
        ), rows)
        if with_gallery:
            connection.execute(sa.text(
                "CREATE TABLE product_images "
                "(id INTEGER PRIMARY KEY, product_id INTEGER REFERENCES products(id), "
                "image_url TEXT, sort_order INTEGER, is_primary BOOLEAN, "
                "UNIQUE (product_id, image_url))"
            ))
            connection.execute(sa.text(
                "INSERT INTO product_images VALUES (:id, :id, :image, 0, 1)"
            ), rows)

        assert repair_image_paths(connection, tmp_path) == {
            "products": len(IMAGE_REPAIRS),
            "product_images": len(IMAGE_REPAIRS) if with_gallery else 0,
            "redundant_gallery_rows": 0,
        }
        assert repair_image_paths(connection, tmp_path) == {
            "products": 0, "product_images": 0, "redundant_gallery_rows": 0,
        }
        after = connection.execute(
            sa.text("SELECT * FROM products ORDER BY id")
        ).mappings().all()
        expected = [dict(row) for row in rows]
        for row, (_, _, new) in zip(expected, IMAGE_REPAIRS):
            row["image"] = PREFIX + new
        assert after == expected
        if with_gallery:
            gallery = connection.execute(sa.text(
                "SELECT id, product_id, image_url, sort_order, is_primary "
                "FROM product_images ORDER BY id"
            )).all()
            assert gallery == [
                (row["id"], row["id"], row["image"], 0, 1) for row in expected
            ]


@pytest.mark.parametrize("primary", [False, True])
def test_gallery_collision_keeps_valid_row_and_rejects_primary_conflict(tmp_path, primary):
    for _, _, filename in IMAGE_REPAIRS:
        path = tmp_path / (PREFIX + filename).lstrip("/")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
    with sa.create_engine("sqlite://").begin() as connection:
        connection.execute(sa.text(
            "CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT, image TEXT)"
        ))
        connection.execute(sa.text(
            "CREATE TABLE product_images (id INTEGER PRIMARY KEY, product_id INTEGER, "
            "image_url TEXT, is_primary BOOLEAN, UNIQUE (product_id, image_url))"
        ))
        name, old, new = IMAGE_REPAIRS[-1]
        connection.execute(sa.text(
            "INSERT INTO products VALUES (1, :name, NULL)"
        ), {"name": name})
        connection.execute(sa.text(
            "INSERT INTO product_images VALUES (:id, 1, :url, :primary)"
        ), [
            {"id": 1, "url": PREFIX + old, "primary": primary},
            {"id": 2, "url": PREFIX + new, "primary": False},
        ])
        if primary:
            with pytest.raises(RuntimeError, match="Primary gallery"):
                repair_image_paths(connection, tmp_path)
            assert connection.scalar(sa.text("SELECT count(*) FROM product_images")) == 2
        else:
            assert repair_image_paths(connection, tmp_path) == {
                "products": 0, "product_images": 0, "redundant_gallery_rows": 1,
            }
            assert connection.execute(sa.text(
                "SELECT id, image_url FROM product_images"
            )).all() == [(2, PREFIX + new)]
            assert repair_image_paths(connection, tmp_path) == {
                "products": 0, "product_images": 0, "redundant_gallery_rows": 0,
            }


def test_missing_asset_aborts_before_writing(tmp_path):
    with sa.create_engine("sqlite://").begin() as connection:
        with pytest.raises(FileNotFoundError, match="photograph is missing"):
            repair_image_paths(connection, tmp_path)


@pytest.mark.parametrize("url", [
    "postgresql://remote.example/ultimatekits",
    "postgresql://localhost/production",
    "sqlite://",
])
def test_repair_refuses_non_development_targets(url):
    with pytest.raises(RuntimeError, match="local"):
        require_local_development_database(make_url(url))


def test_repair_refuses_non_debug_mode(monkeypatch):
    from scripts.repair_club_image_paths import settings

    monkeypatch.setattr(settings, "DEBUG", False)
    with pytest.raises(RuntimeError, match="local"):
        require_local_development_database(make_url(settings.DATABASE_URL))


def test_corrected_photographs_exist_with_expected_formats():
    if not FRONTEND_PUBLIC.is_dir():
        pytest.skip("Frontend checkout is not available")
    for _, _, filename in IMAGE_REPAIRS:
        path = FRONTEND_PUBLIC / (PREFIX + filename).lstrip("/")
        header = path.read_bytes()[:12]
        if filename.endswith(".webp"):
            assert header[:4] == b"RIFF" and header[8:] == b"WEBP"
        else:
            assert header[:2] == b"\xff\xd8"


@pytest.mark.parametrize("name,filename", [
    ("Chelsea Home Jersey", "chelsea-home.webp"),
    (
        "Manchester United Red Jersey - Black Shoulder Stripes",
        "manchester-united-home22.jpg",
    ),
])
def test_repaired_image_is_returned_on_list_and_detail(client, db, name, filename):
    from app.models.product import Product

    product = db.query(Product).filter(Product.name == name).first()
    if product is None:
        product = Product(
            name=name, sport="Football", category="Jerseys", price="25000.00"
        )
        db.add(product)
    product.image = PREFIX + filename
    db.commit()
    detail = client.get(f"/products/{product.id}")
    assert detail.status_code == 200
    assert detail.json()["image"] == PREFIX + filename
    catalog = client.get("/products")
    assert catalog.status_code == 200
    assert next(
        row for row in catalog.json() if row["id"] == product.id
    )["image"] == PREFIX + filename
