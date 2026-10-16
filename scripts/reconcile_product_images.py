"""Inventory public product images and reconcile approved catalog links."""

import argparse
import csv
import hashlib
import struct
import sys
from collections import defaultdict
from pathlib import Path

from sqlalchemy import inspect, text
from sqlalchemy.engine import make_url

API_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_ROOT))

from app.core.config import settings
from app.database.database import SessionLocal
from app.database.seed import (
    PRODUCTS,
    PRODUCT_GALLERY_IMAGES,
    seed_products,
    seed_development_catalog,
)
from app.database.development_catalog import NEW_PRODUCTS, require_development_database
from app.models.product import Product
from app.models.product_image import ProductImage


REPOSITORY_ROOT = API_ROOT.parent
FRONTEND_PUBLIC = REPOSITORY_ROOT / "ultimateKits-FE" / "public"
IMAGE_ROOT = FRONTEND_PUBLIC / "images" / "products"
REPORT_PATH = (
    REPOSITORY_ROOT
    / "ultimateKits-FE"
    / "docs"
    / "product-image-reconciliation.csv"
)
PRICE_REPORT_PATH = API_ROOT / "docs" / "development-product-prices.csv"
SUPPORTED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif",
    ".bmp",
    ".avif",
}
RENAMED_FROM = {
    "football/manchester-united-home-close-up.webp":
        "football/chelsea-home.webp",
    "football/manchester-united-home-model.webp":
        "football/chelsea-home2.webp",
    "football/manchester-united-home-front.webp":
        "football/chelsea-home-back.webp",
    "football/chelsea-home-detail.webp":
        "football/chelsea-home11.webp",
    "football/chelsea-home-front.webp":
        "football/manchester-united-home-away.webp",
    "football/chelsea-home-back.webp":
        "football/manchester-united-home-closeup2.webp",
}
def image_dimensions(path: Path) -> str:
    """Read dimensions from JPEG and WebP headers without extra packages."""
    try:
        with path.open("rb") as image:
            header = image.read(12)
            if header[:2] == b"\xff\xd8":
                image.seek(2)
                while True:
                    marker_prefix = image.read(1)
                    if not marker_prefix:
                        return ""
                    if marker_prefix != b"\xff":
                        continue
                    marker = image.read(1)
                    while marker == b"\xff":
                        marker = image.read(1)
                    if marker in {b"\xd8", b"\xd9"}:
                        continue
                    length_data = image.read(2)
                    if len(length_data) != 2:
                        return ""
                    length = struct.unpack(">H", length_data)[0]
                    segment = image.read(length - 2)
                    if marker[0] in {
                        0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6,
                        0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF,
                    }:
                        height, width = struct.unpack(">HH", segment[1:5])
                        return f"{width}x{height}"
            if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
                while True:
                    chunk_header = image.read(8)
                    if len(chunk_header) != 8:
                        return ""
                    chunk, length_data = chunk_header[:4], chunk_header[4:]
                    length = struct.unpack("<I", length_data)[0]
                    data = image.read(length)
                    if length % 2:
                        image.read(1)
                    if chunk == b"VP8X" and len(data) >= 10:
                        width = int.from_bytes(data[4:7], "little") + 1
                        height = int.from_bytes(data[7:10], "little") + 1
                        return f"{width}x{height}"
                    if chunk == b"VP8 " and len(data) >= 10:
                        width = int.from_bytes(data[6:8], "little") & 0x3FFF
                        height = int.from_bytes(data[8:10], "little") & 0x3FFF
                        return f"{width}x{height}"
                    if chunk == b"VP8L" and len(data) >= 5 and data[0] == 0x2F:
                        width = 1 + data[1] + ((data[2] & 0x3F) << 8)
                        height = (
                            1
                            + ((data[2] & 0xC0) >> 6)
                            + (data[3] << 2)
                            + ((data[4] & 0x0F) << 10)
                        )
                        return f"{width}x{height}"
    except OSError:
        return ""
    return ""


def image_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as image:
        for chunk in iter(lambda: image.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def catalog_image_map(db) -> dict[str, list[tuple[str, str]]]:
    records: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for image in db.query(ProductImage).join(Product).all():
        kind = "primary" if image.is_primary else "alternate"
        records[image.image_url].append((image.product.name, kind))
    return records


def public_image_file(image_url: str) -> Path | None:
    prefix = "/images/products/"
    if not image_url.startswith(prefix):
        return None

    public_root = FRONTEND_PUBLIC.resolve()
    candidate = (FRONTEND_PUBLIC / image_url.lstrip("/")).resolve()
    try:
        candidate.relative_to(public_root)
    except ValueError:
        return None
    return candidate


def image_exists(image_url: str) -> bool:
    image_file = public_image_file(image_url)
    return image_file is not None and image_file.is_file()


def missing_seed_images() -> list[str]:
    missing = []
    for product in PRODUCTS:
        paths = [product["image"]]
        paths.extend(PRODUCT_GALLERY_IMAGES.get(product["name"], []))
        missing.extend(
            image_url
            for image_url in paths
            if not image_exists(image_url)
        )
    for entry in NEW_PRODUCTS:
        missing.extend(path for path in entry.paths if not image_exists(path))
    return missing


def fallback_note(relative_path: str) -> str:
    unresolved = {
        "football/haaland-blue.jpg":
            "Player portrait; shirt details differ from the standalone Manchester City image. Exact design association unresolved.",
        "football/james-blue.webp":
            "Player portrait includes a central winner-style badge absent from the Chelsea primary. Exact variant association unresolved.",
        "national-teams/haaland-norway.jpg":
            "Player portrait; shirt cut/pattern cannot be confirmed identical to the standalone Norway product. Not a confirmed pre-printed sellable item.",
        "national-teams/lamineyamal-spain.jpg":
            "Player/event photograph with printing/badges; cannot confirm same design as framed Spain Home image. No separate player listing inferred.",
        "national-teams/messi-argentina.jpg":
            "Combined home/away image depicts two products, not one sellable bundle; separate home/away records use their own photographs.",
    }
    if relative_path in unresolved:
        return unresolved[relative_path]
    entry = next((item for item in NEW_PRODUCTS if relative_path in (item.image, *item.alternates)), None)
    if entry:
        return "Reviewed development design not seeded yet. Run the guarded --apply --development-catalog command."
    return (
        "Unrecognized image identity; classify before adding a product or gallery association."
    )


def likely_subject(relative_path: str) -> str:
    if relative_path.startswith("national-teams/"):
        stem = Path(relative_path).stem.replace("-", " ").title()
        if stem.startswith("Brasil ") or stem.startswith("Brazil "):
            return "Brazil"
        if stem.startswith("Messi "):
            return "Argentina player photo"
        if stem.startswith("Lamineyamal "):
            return "Spain player photo"
        if stem.startswith("Haaland "):
            return "Norway player photo"
        return stem.split(" ")[0]
    if relative_path.startswith("basketball/"):
        return Path(relative_path).stem.replace("-", " ").title()
    if relative_path.startswith("generic/"):
        return Path(relative_path).stem.replace("-", " ").title()
    return Path(relative_path).stem.replace("-", " ").title()


def write_inventory(db) -> tuple[int, int, dict[str, int]]:
    rows_by_path = catalog_image_map(db)
    files = sorted(
        path
        for path in IMAGE_ROOT.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )
    hashes: dict[str, list[str]] = defaultdict(list)
    for path in files:
        hashes[image_hash(path)].append(path.relative_to(IMAGE_ROOT).as_posix())

    counts: dict[str, int] = defaultdict(int)
    unmatched = 0
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with REPORT_PATH.open("w", newline="", encoding="utf-8") as report:
        writer = csv.DictWriter(
            report,
            fieldnames=[
                "original_path",
                "filename",
                "canonical_path",
                "format",
                "dimensions",
                "likely_product_or_team",
                "folder_classification",
                "catalog_association",
                "status",
                "notes",
            ],
        )
        writer.writeheader()
        for path in files:
            relative = path.relative_to(IMAGE_ROOT).as_posix()
            url = f"/images/products/{relative}"
            associations = rows_by_path.get(url, [])
            duplicate_paths = hashes[image_hash(path)]
            duplicate_associations = [
                (other, rows_by_path[f"/images/products/{other}"])
                for other in duplicate_paths
                if other != relative and f"/images/products/{other}" in rows_by_path
            ]
            is_associated = bool(associations)
            if is_associated:
                status = "associated"
                association = "; ".join(
                    f"{name} ({kind})" for name, kind in associations
                )
                entry = next((item for item in NEW_PRODUCTS if url in item.paths), None)
                notes = (
                    entry.note if entry and entry.note
                    else "Visually matched catalog design; numbered listings describe visible fixed printing, not personalization."
                )
                if relative == "football/manchester-united-home-33.jpg":
                    notes = "Alternate collared-home-shirt photograph. Filename 33 is not a visible number or separate product."
            elif duplicate_associations:
                status = "duplicate_file"
                association = "; ".join(
                    f"{name} (duplicate file of /images/products/{other})"
                    for other, matches in duplicate_associations
                    for name, _kind in matches
                )
                notes = "Identical SHA-256 bytes; preserved on disk, deliberately not linked as a redundant gallery row."
            else:
                status = "unmatched"
                association = ""
                notes = fallback_note(relative)
                if len(hashes[image_hash(path)]) > 1:
                    duplicates = [
                        other
                        for other in hashes[image_hash(path)]
                        if other != relative
                    ]
                    notes += " Exact duplicate bytes: " + ", ".join(
                        f"/images/products/{other}" for other in duplicates
                    )
                unmatched += 1

            folder = relative.split("/", 1)[0]
            counts[folder] += 1
            original_path = RENAMED_FROM.get(relative, relative)
            writer.writerow(
                {
                    "original_path": f"/images/products/{original_path}",
                    "filename": path.name,
                    "canonical_path": f"/images/products/{relative}",
                    "format": path.suffix.lower().lstrip("."),
                    "dimensions": image_dimensions(path),
                    "likely_product_or_team": (
                        associations[0][0] if associations else likely_subject(relative)
                    ),
                    "folder_classification": folder,
                    "catalog_association": association,
                    "status": status,
                    "notes": notes,
                }
            )

    return len(files), unmatched, dict(counts)


def write_price_register(db) -> None:
    PRICE_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with PRICE_REPORT_PATH.open("w", newline="", encoding="utf-8") as report:
        writer = csv.DictWriter(report, fieldnames=[
            "catalog_key", "product_id", "product_name", "currency",
            "temporary_ngn_price", "current_ngn_price", "development_placeholder",
            "price_status", "sport", "category", "league",
        ])
        writer.writeheader()
        for product in db.query(Product).order_by(Product.id).all():
            writer.writerow({
                "catalog_key": product.catalog_key or "",
                "product_id": product.id,
                "product_name": product.name,
                "currency": "NGN",
                "temporary_ngn_price": (
                    f"{product.price:.2f}" if product.development_placeholder else ""
                ),
                "current_ngn_price": f"{product.price:.2f}",
                "development_placeholder": str(product.development_placeholder).lower(),
                "price_status": (
                    "development_only_not_production_approved"
                    if product.development_placeholder
                    else "approved_retro_price" if product.name in {
                        row["name"] for row in PRODUCTS if row["category"] == "Retro"
                    } else "existing_price_preserved"
                ),
                "sport": product.sport,
                "category": product.category,
                "league": product.league or "",
            })


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Run the idempotent approved-product and gallery seed.",
    )
    parser.add_argument(
        "--development-catalog", action="store_true",
        help="Include all visually reviewed designs with authorized NGN development prices.",
    )
    parser.add_argument(
        "--check-production-prices", action="store_true",
        help="Read-only deployment preflight: fail while any placeholder prices remain.",
    )
    args = parser.parse_args()
    if args.check_production_prices and (args.apply or args.development_catalog):
        parser.error("--check-production-prices cannot be combined with seed options.")

    db_url = make_url(settings.DATABASE_URL)
    if args.apply and not (
        db_url.host in {"localhost", "127.0.0.1", "::1"}
        and db_url.database == "ultimatekits"
    ):
        raise SystemExit(
            "Refusing catalog writes: the configured database is not "
            "the confirmed local ultimatekits development database."
        )

    db = SessionLocal()
    try:
        if args.apply:
            require_development_database(db)
        if not inspect(db.bind).has_table("product_images"):
            raise SystemExit(
                "The product image gallery migration is not applied; "
                "run `alembic upgrade head` first."
            )
        revision = db.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one()
        from alembic.config import Config
        from alembic.script import ScriptDirectory
        config = Config(str(API_ROOT / "alembic.ini"))
        config.set_main_option("script_location", str(API_ROOT / "alembic"))
        if revision != ScriptDirectory.from_config(config).get_current_head():
            raise SystemExit("Apply `python -m alembic upgrade head` before catalog operations.")
        if args.check_production_prices:
            pending = db.query(Product).filter(Product.development_placeholder.is_(True)).all()
            if pending:
                raise SystemExit(
                    "Production price preflight FAILED: replace placeholder prices "
                    "through authenticated PATCH /products/{id}: "
                    + ", ".join(str(product.id) for product in pending)
                )
            print("Production price preflight passed: no development placeholders.")
            return
        missing_seed = missing_seed_images() if args.apply else []
        if missing_seed:
            raise SystemExit(
                "Refusing to seed because approved image files are missing: "
                + ", ".join(missing_seed)
            )

        before_products = db.query(Product).count()
        before_images = db.query(ProductImage).count()
        seed_summary = {"products_created": 0, "gallery_images_created": 0}
        if args.apply:
            seed_summary = (
                seed_development_catalog(db) if args.development_catalog
                else seed_products(db)
            )
            db.flush()

        files, unmatched, folder_counts = write_inventory(db)
        after_products = db.query(Product).count()
        after_images = db.query(ProductImage).count()
        products = db.query(Product).all()
        broken_paths = [
            image.image_url
            for image in db.query(ProductImage).all()
            if not image_exists(image.image_url)
        ]
        broken_primary_paths = [
            product.image
            for product in products
            if product.image and not image_exists(product.image)
        ]
        products_without_primary_gallery = [
            product.name
            for product in products
            if product.image
            and not any(
                image.is_primary and image.image_url == product.image
                for image in product.product_images
            )
        ]
        if broken_paths or broken_primary_paths or products_without_primary_gallery:
            db.rollback()
            raise SystemExit(
                "Catalog image validation failed; all seed changes rolled back: "
                + repr((broken_paths, broken_primary_paths, products_without_primary_gallery))
            )
        if args.apply:
            db.commit()
        write_price_register(db)

        print(
            f"Database target: {db_url.host}/{db_url.database}; "
            f"migration={revision}"
        )
        print(
            f"Image inventory: {files} files by folder "
            f"{dict(sorted(folder_counts.items()))}; "
            f"unmatched={unmatched}"
        )
        print(
            f"Products: {before_products} -> {after_products}; "
            f"created={seed_summary['products_created']}; "
            f"prices_updated={seed_summary.get('prices_updated', 0)}"
        )
        print(
            f"Gallery entries: {before_images} -> {after_images}; "
            f"created={seed_summary['gallery_images_created']}"
        )
        print(
            f"Broken gallery paths: {len(broken_paths)}"
            + (f" ({', '.join(broken_paths)})" if broken_paths else "")
        )
        print(
            f"Broken product primary paths: {len(broken_primary_paths)}"
            + (
                f" ({', '.join(broken_primary_paths)})"
                if broken_primary_paths
                else ""
            )
        )
        print(
            "Products without matching primary gallery rows: "
            f"{len(products_without_primary_gallery)}"
            + (
                f" ({', '.join(products_without_primary_gallery)})"
                if products_without_primary_gallery
                else ""
            )
        )
        print(f"Inventory report: {REPORT_PATH}")
        print(f"Development price register (output only): {PRICE_REPORT_PATH}")
        if broken_paths or broken_primary_paths or products_without_primary_gallery:
            raise SystemExit(1)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
