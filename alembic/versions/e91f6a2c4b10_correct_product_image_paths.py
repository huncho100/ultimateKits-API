"""correct product image paths

Revision ID: e91f6a2c4b10
Revises: d8b3e45c7a91
Create Date: 2026-10-09

Correct product image paths to files in the frontend's
public product-image directory. Paths not backed by a
file in that directory are cleared.
"""

from collections import defaultdict
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "e91f6a2c4b10"
down_revision: Union[str, Sequence[str], None] = "d8b3e45c7a91"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_VALID_IMAGE_PATHS = frozenset(
    {
        "/images/products/basketball/bulls-red.jpg",
        "/images/products/basketball/celtic-black.jpg",
        "/images/products/basketball/celtic-black2.jpg",
        "/images/products/basketball/celtic-green.jpg",
        "/images/products/basketball/cleveland-red.jpg",
        "/images/products/basketball/dallas-white.jpg",
        "/images/products/basketball/goldenstate-white.jpg",
        "/images/products/basketball/heat-white.jpg",
        "/images/products/basketball/lakers-white.jpg",
        "/images/products/basketball/lakers-yello.jpg",
        "/images/products/basketball/rockets-white.jpg",
        "/images/products/football/arsenal-home.jpg",
        "/images/products/football/barcelona-home.jpg",
        "/images/products/football/bayern-munich-home.jpg",
        "/images/products/football/chelsea-home.webp",
        "/images/products/football/chelsea-home1.webp",
        "/images/products/football/chelsea-home2.webp",
        "/images/products/football/chelsea-home-back.webp",
        "/images/products/football/haaland-blue.jpg",
        "/images/products/football/inter-milan-home.jpg",
        "/images/products/football/james-blue.webp",
        "/images/products/football/liverpool-home-close-up.jpg",
        "/images/products/football/liverpool-home-close-up2.jpg",
        "/images/products/football/liverpool-home.jpg",
        "/images/products/football/manchester-city-home.jpg",
        "/images/products/football/manchester-united-home-25.jpg",
        "/images/products/football/manchester-united-home-away.webp",
        "/images/products/football/manchester-united-home-closeup2.webp",
        "/images/products/football/manchester-united-home.jpg",
        "/images/products/football/manchester-united-home2.webp",
        "/images/products/football/manchester-united-home3.webp",
        "/images/products/football/psg-home.jpg",
        "/images/products/football/real-madrid-home2.jpg",
        "/images/products/generic/dallas-white.jpg",
        "/images/products/generic/gen-2.jpg",
        "/images/products/generic/gen-3.jpg",
        "/images/products/generic/gen-4.jpg",
        "/images/products/generic/heat-white.jpg",
        "/images/products/generic/rockets-white.jpg",
        "/images/products/generic/spurs-blue.jpg",
        "/images/products/national-teams/argentina-away.jpg",
        "/images/products/national-teams/argentina-home.jpg",
        "/images/products/national-teams/brasil-away2.jpg",
        "/images/products/national-teams/brazil-away.jpg",
        "/images/products/national-teams/brazil-home.jpg",
        "/images/products/national-teams/france-away.jpg",
        "/images/products/national-teams/france-home.jpg",
        "/images/products/national-teams/germany-away.jpg",
        "/images/products/national-teams/germany-away2.jpg",
        "/images/products/national-teams/germany-home.jpg",
        "/images/products/national-teams/haaland-norway.jpg",
        "/images/products/national-teams/lamineyamal-spain.jpg",
        "/images/products/national-teams/messi-argentina.jpg",
        "/images/products/national-teams/nigeria-1996.jpg",
        "/images/products/national-teams/nigeria-green.jpg",
        "/images/products/national-teams/nigeria-green2.jpg",
        "/images/products/national-teams/nigeria-home.jpg",
        "/images/products/national-teams/nigeria-nike.jpg",
        "/images/products/national-teams/nigeria-white.jpg",
        "/images/products/national-teams/nigeria-white2.jpg",
        "/images/products/national-teams/nigeria-white3.jpg",
        "/images/products/national-teams/nigeria-women-green.jpg",
        "/images/products/national-teams/norway-home.jpg",
        "/images/products/national-teams/portugal-away.jpg",
        "/images/products/national-teams/portugal-home.jpg",
        "/images/products/national-teams/portugal-red.jpg",
        "/images/products/national-teams/spain-away.jpg",
        "/images/products/national-teams/spain-home.jpg",
        "/images/products/retro/barca-retro.jpg",
        "/images/products/retro/england-retro.jpg",
        "/images/products/retro/inter-retro.jpg",
        "/images/products/retro/liverpool-retro.jpg",
        "/images/products/retro/nigeria-retro-green.jpg",
        "/images/products/retro/nigeria-retro.jpg",
        "/images/products/retro/nigeria-white.jpg",
    }
)

_PRODUCT_IMAGE_BY_NAME = {
    "Real Madrid Home Jersey": (
        "/images/products/football/real-madrid-home2.jpg"
    ),
    "Liverpool Home Jersey": (
        "/images/products/football/liverpool-home.jpg"
    ),
    "Bayern Munich Home Jersey": (
        "/images/products/football/bayern-munich-home.jpg"
    ),
    "Inter Milan Home Jersey": (
        "/images/products/football/inter-milan-home.jpg"
    ),
    "Paris Saint-Germain Home Jersey": (
        "/images/products/football/psg-home.jpg"
    ),
}


def _legacy_image_paths() -> dict[str, str]:
    paths_by_filename: dict[str, list[str]] = defaultdict(list)
    for path in _VALID_IMAGE_PATHS:
        paths_by_filename[path.rsplit("/", 1)[1]].append(path)

    return {
        f"/images/{filename}": paths[0]
        for filename, paths in paths_by_filename.items()
        if len(paths) == 1
    }


def upgrade() -> None:
    products = sa.table(
        "products",
        sa.column("name", sa.String()),
        sa.column("image", sa.String()),
    )
    connection = op.get_bind()

    connection.execute(
        products.update()
        .where(products.c.name.in_(_PRODUCT_IMAGE_BY_NAME))
        .values(
            image=sa.case(
                _PRODUCT_IMAGE_BY_NAME,
                value=products.c.name,
            )
        )
    )

    legacy_paths = _legacy_image_paths()
    connection.execute(
        products.update()
        .where(products.c.image.in_(legacy_paths))
        .values(
            image=sa.case(
                legacy_paths,
                value=products.c.image,
            )
        )
    )

    connection.execute(
        products.update()
        .where(
            products.c.image.is_not(None),
            products.c.image.not_in(_VALID_IMAGE_PATHS),
        )
        .values(image=None)
    )


def downgrade() -> None:
    # Restoring the old URLs would reintroduce broken product images.
    pass
