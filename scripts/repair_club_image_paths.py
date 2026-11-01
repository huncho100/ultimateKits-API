"""Repair confirmed stale club image URLs without seeding or changing products."""

import argparse
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.engine import Connection, URL, make_url

from app.core.config import settings
from app.database.database import engine


FRONTEND_PUBLIC = (
    Path(__file__).resolve().parents[2] / "ultimateKits-FE" / "public"
)
PREFIX = "/images/products/football/"

# Match both identity and stale URL; never replace a valid custom image.
# Each correct file is byte-identical (same Git blob) to the photograph the
# stale path used to name, so no photograph is substituted by guesswork.
IMAGE_REPAIRS = (
    ("Chelsea Home Jersey", "chelsea-home.webp", "chelsea-home-front.webp"),
    (
        "Manchester United Red Jersey - Black Shoulder Stripes",
        "manchester-united-home22.jpg",
        "manchester-united-home11.jpg",
    ),
    ("Chelsea Home Jersey", "chelsea-home2.webp", "chelsea-home-detail.webp"),
    (
        "Manchester United Home Jersey",
        "manchester-united-home-closeup2.webp",
        "manchester-united-home-front.webp",
    ),
    (
        "Manchester United Home Jersey",
        "manchester-united-home3.webp",
        "manchester-united-home.webp",
    ),
)


def require_local_development_database(url: URL) -> None:
    if not (
        settings.DEBUG
        and url == make_url(settings.DATABASE_URL)
        and url.get_backend_name() == "postgresql"
        and url.host in {"localhost", "127.0.0.1", "::1"}
        and url.database == "ultimatekits"
    ):
        raise RuntimeError(
            "Image repair requires DEBUG=True and the configured local "
            "PostgreSQL ultimatekits database. No remote database is allowed."
        )


def repair_image_paths(
    connection: Connection,
    public: Path = FRONTEND_PUBLIC,
) -> dict[str, int]:
    for _, _, filename in IMAGE_REPAIRS:
        path = public / (PREFIX + filename).lstrip("/")
        if not path.is_file():
            raise FileNotFoundError(f"Required product photograph is missing: {path}")

    metadata = sa.MetaData()
    products = sa.Table("products", metadata, autoload_with=connection)
    # Some development databases retain galleries from the newer catalog branch.
    gallery = (
        sa.Table("product_images", metadata, autoload_with=connection)
        if sa.inspect(connection).has_table("product_images")
        else None
    )
    counts = {"products": 0, "product_images": 0, "redundant_gallery_rows": 0}
    for name, old, new in IMAGE_REPAIRS:
        counts["products"] += connection.execute(
            products.update()
            .where(products.c.name == name, products.c.image == PREFIX + old)
            .values(image=PREFIX + new)
        ).rowcount
        if gallery is not None:
            stale_rows = connection.execute(
                sa.select(gallery).where(
                    gallery.c.product_id.in_(
                        sa.select(products.c.id).where(products.c.name == name)
                    ),
                    gallery.c.image_url == PREFIX + old,
                )
            ).mappings().all()
            for row in stale_rows:
                existing = connection.execute(
                    sa.select(gallery.c.id).where(
                        gallery.c.product_id == row["product_id"],
                        gallery.c.image_url == PREFIX + new,
                    )
                ).first()
                if existing is not None:
                    if row["is_primary"]:
                        raise RuntimeError(
                            "Primary gallery repair would collide with an existing "
                            "image; resolve its ordering explicitly before retrying."
                        )
                    # Keep the already-valid alternate and remove only its broken alias.
                    counts["redundant_gallery_rows"] += connection.execute(
                        gallery.delete().where(gallery.c.id == row["id"])
                    ).rowcount
                else:
                    counts["product_images"] += connection.execute(
                        gallery.update().where(gallery.c.id == row["id"])
                        .values(image_url=PREFIX + new)
                    ).rowcount
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply", action="store_true", help="Commit repairs (default: dry run)."
    )
    args = parser.parse_args()
    require_local_development_database(engine.url)
    print("Target: local PostgreSQL ultimatekits; mode:", "apply" if args.apply else "dry run")
    with engine.connect() as connection, connection.begin() as transaction:
        counts = repair_image_paths(connection)
        if not args.apply:
            transaction.rollback()
    print("Committed:" if args.apply else "Would update:", counts)


if __name__ == "__main__":
    main()
