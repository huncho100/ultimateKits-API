import csv
import re

from app.database.seed import seed_development_catalog
from app.models.product import Product
from app.models.product_image import ProductImage
from scripts import reconcile_product_images


def test_image_dimensions_cover_current_jpeg_and_webp_assets():
    jpeg = (
        reconcile_product_images.IMAGE_ROOT
        / "football"
        / "liverpool-home.jpg"
    )
    webp = (
        reconcile_product_images.IMAGE_ROOT
        / "football"
        / "manchester-united-home.webp"
    )

    assert re.fullmatch(r"\d+x\d+", reconcile_product_images.image_dimensions(jpeg))
    assert re.fullmatch(r"\d+x\d+", reconcile_product_images.image_dimensions(webp))


def test_report_accounts_for_every_asset_and_database_association(
    db,
    monkeypatch,
    tmp_path,
):
    seed_development_catalog(db)
    db.commit()
    report_path = tmp_path / "product-image-reconciliation.csv"
    monkeypatch.setattr(
        reconcile_product_images,
        "REPORT_PATH",
        report_path,
    )

    file_count, unmatched_count, folders = (
        reconcile_product_images.write_inventory(db)
    )

    with report_path.open(encoding="utf-8", newline="") as report:
        rows = list(csv.DictReader(report))

    assert file_count == len(rows) == 74
    assert unmatched_count == 5
    assert folders == {
        "basketball": 11,
        "football": 21,
        "generic": 7,
        "national-teams": 28,
        "retro": 7,
    }
    assert sum(row["status"] == "associated" for row in rows) == 65
    assert sum(row["status"] == "duplicate_file" for row in rows) == 4
    assert all(row["dimensions"] for row in rows)
    assert all(
        row["canonical_path"].startswith("/images/products/")
        for row in rows
    )


def test_product_primary_paths_resolve_to_primary_gallery_rows(db):
    public_root = reconcile_product_images.FRONTEND_PUBLIC

    for product in db.query(Product).all():
        if product.image is None:
            continue

        primary_images = [
            image
            for image in product.product_images
            if image.is_primary
        ]
        assert len(primary_images) == 1
        assert primary_images[0].image_url == product.image
        assert (public_root / product.image.lstrip("/")).is_file()

    assert db.query(ProductImage).count() == 23
