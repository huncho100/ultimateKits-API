"""Explicit, development-only catalog identities and visually reviewed designs."""

import re
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core.config import settings


def catalog_key(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def require_development_database(db: Session) -> None:
    url = db.get_bind().engine.url
    if url.drivername == "sqlite" and url.database in {None, "", ":memory:"}:
        return
    configured = make_url(settings.DATABASE_URL)
    if not (
        settings.DEBUG
        and url.get_backend_name() == "postgresql"
        and url.host in {"localhost", "127.0.0.1", "::1"}
        and url.database == "ultimatekits"
        and url == configured
    ):
        raise RuntimeError(
            "Development catalog seeding requires DEBUG=True and the configured "
            "local PostgreSQL ultimatekits database. Production seeding is refused."
        )


@dataclass(frozen=True)
class CatalogEntry:
    name: str
    team: str
    image: str
    sport: str = "Football"
    category: str = "Jerseys"
    league: str | None = "National Team"
    alternates: tuple[str, ...] = ()
    note: str = ""

    @property
    def key(self) -> str:
        return catalog_key(self.name)

    @property
    def price(self) -> Decimal:
        return {
            "Football": Decimal("25000.00"),
            "Basketball": Decimal("20000.00"),
            "Baseball": Decimal("22500.00"),
        }[self.sport]

    @property
    def paths(self) -> list[str]:
        return [f"/images/products/{path}" for path in (self.image, *self.alternates)]


# Numbers describe visible pre-printing, not an offered personalization service.
# No seasons, editions, licensing, descriptions, ratings or counted stock are inferred.
NEW_PRODUCTS = (
    CatalogEntry(
        "Manchester City Home Jersey", "Manchester City",
        "football/manchester-city-home.jpg", league="Premier League",
    ),
    CatalogEntry(
        "Manchester United Red Jersey - Black Shoulder Stripes", "Manchester United",
        "football/manchester-united-home11.jpg", league="Premier League",
        note="Different collar/black shoulder stripes from the existing collared home shirt; no season inferred.",
    ),
    CatalogEntry("Argentina Home Jersey - No. 10", "Argentina", "national-teams/argentina-home.jpg"),
    CatalogEntry("Argentina Away Jersey - No. 10", "Argentina", "national-teams/argentina-away.jpg"),
    CatalogEntry("Brazil Home Jersey", "Brazil", "national-teams/brazil-home.jpg"),
    CatalogEntry(
        "Brazil Away Jersey", "Brazil", "national-teams/brasil-away2.jpg",
        note="Unnumbered design; not an alternate for the separately depicted No. 7 item.",
    ),
    CatalogEntry("Brazil Away Jersey - No. 7", "Brazil", "national-teams/brazil-away.jpg"),
    CatalogEntry("France Home Jersey", "France", "national-teams/france-home.jpg"),
    CatalogEntry("France Away Jersey - No. 10", "France", "national-teams/france-away.jpg"),
    CatalogEntry(
        "Germany Away Jersey", "Germany", "national-teams/germany-away.jpg",
        alternates=("national-teams/germany-away2.jpg",),
        note="Matching teal-trimmed design; alternate product photograph.",
    ),
    CatalogEntry("Germany Home Jersey - No. 17", "Germany", "national-teams/germany-home.jpg"),
    CatalogEntry(
        "Nigeria Classic Jersey - Green/White No. 22", "Nigeria",
        "national-teams/nigeria-1996.jpg", category="Retro",
        note="Previously approved Retro classification and printing. No year claimed; actual file depicts green/white No. 22.",
    ),
    CatalogEntry(
        "Nigeria Green Jersey", "Nigeria", "national-teams/nigeria-green.jpg",
        alternates=("national-teams/nigeria-women-green.jpg",),
        note="Same light/dark-green design with alternate front/back views. Filename alone does not establish gender or fit.",
    ),
    CatalogEntry(
        "Nigeria Dark Green Jersey", "Nigeria", "national-teams/nigeria-green2.jpg",
        note="Different dark-green design and patterned collar; not an alternate of the light-green shirt.",
    ),
    CatalogEntry(
        "Nigeria White/Green Flame Jersey", "Nigeria", "national-teams/nigeria-white.jpg",
        alternates=("national-teams/nigeria-home.jpg", "national-teams/nigeria-white2.jpg"),
        note="Same flame design photographed on white background, hanger and mannequin. Retro duplicate bytes are not linked again.",
    ),
    CatalogEntry(
        "Nigeria White Jersey", "Nigeria", "national-teams/nigeria-white3.jpg",
        note="Plain white design with green sleeve bands; distinct from flame and approved Retro White designs.",
    ),
    CatalogEntry(
        "Nigeria White/Green Patterned Jersey", "Nigeria", "national-teams/nigeria-nike.jpg",
        note="Black/green brush-pattern detail depicts a different design from the flame shirt; no season inferred.",
    ),
    CatalogEntry(
        "Norway Home Jersey", "Norway", "national-teams/norway-home.jpg",
        note="Red/blue/white cross design; player photograph remains unmatched because its cut/pattern cannot be confirmed identical.",
    ),
    CatalogEntry(
        "Portugal Home Jersey", "Portugal", "national-teams/portugal-home.jpg",
        alternates=("national-teams/portugal-red.jpg",),
        note="Matching red design and black trim; image date is not treated as verified season metadata.",
    ),
    CatalogEntry("Portugal Away Jersey", "Portugal", "national-teams/portugal-away.jpg"),
    CatalogEntry(
        "Spain Home Jersey", "Spain", "national-teams/spain-home.jpg",
        note="No season inferred from marketing frame; player photograph is not assumed to depict this exact design.",
    ),
    CatalogEntry("Spain Away Jersey - No. 19", "Spain", "national-teams/spain-away.jpg"),
    CatalogEntry("Chicago Bulls Red Jersey - No. 23", "Chicago Bulls", "basketball/bulls-red.jpg", sport="Basketball", league="NBA"),
    CatalogEntry(
        "Boston Celtics Black Jersey - No. 0", "Boston Celtics",
        "basketball/celtic-black.jpg", sport="Basketball", league="NBA",
        alternates=("basketball/celtic-black2.jpg",),
    ),
    CatalogEntry("Boston Celtics Green Jersey - No. 33", "Boston Celtics", "basketball/celtic-green.jpg", sport="Basketball", league="NBA"),
    CatalogEntry("Cleveland Cavaliers Red Jersey - No. 23", "Cleveland Cavaliers", "basketball/cleveland-red.jpg", sport="Basketball", league="NBA"),
    CatalogEntry(
        "Dallas Mavericks White Jersey - No. 77", "Dallas Mavericks",
        "basketball/dallas-white.jpg", sport="Basketball", league="NBA",
        note="Generic folder copy is byte-identical and not a separate product/gallery row.",
    ),
    CatalogEntry("Golden State Warriors White Jersey - No. 30", "Golden State Warriors", "basketball/goldenstate-white.jpg", sport="Basketball", league="NBA"),
    CatalogEntry(
        "Miami Heat White Jersey - No. 22", "Miami Heat",
        "basketball/heat-white.jpg", sport="Basketball", league="NBA",
        note="Front/back composite of one pre-printed item; generic copy is byte-identical.",
    ),
    CatalogEntry("Los Angeles Lakers White Jersey - No. 24", "Los Angeles Lakers", "basketball/lakers-white.jpg", sport="Basketball", league="NBA"),
    CatalogEntry("Los Angeles Lakers Yellow Jersey - No. 23", "Los Angeles Lakers", "basketball/lakers-yello.jpg", sport="Basketball", league="NBA"),
    CatalogEntry(
        "Houston Rockets White Jersey - No. 13", "Houston Rockets",
        "basketball/rockets-white.jpg", sport="Basketball", league="NBA",
        note="Front/back composite of one pre-printed item; generic copy is byte-identical.",
    ),
    CatalogEntry(
        "San Antonio Spurs Black Jersey - No. 21", "San Antonio Spurs",
        "generic/spurs-blue.jpg", sport="Basketball", league="NBA",
        note="Photograph is black/grey despite blue filename; not reclassified as football.",
    ),
    CatalogEntry(
        "New York Yankees Black Jersey - No. 99", "New York Yankees",
        "generic/gen-2.jpg", sport="Baseball", league="MLB",
        note="Yankees crest and pre-printed 99 visible; front/back composite of one item.",
    ),
    CatalogEntry(
        "New York Yankees Pinstripe Jersey - No. 22", "New York Yankees",
        "generic/gen-3.jpg", sport="Baseball", league="MLB",
        note="Pinstripe Yankees design with pre-printed 22; separate from black/grey designs.",
    ),
    CatalogEntry(
        "New York Grey Baseball Jersey", "New York",
        "generic/gen-4.jpg", sport="Baseball", league=None,
        note="NEW YORK wordmark and baseball cut visible; exact franchise is not asserted.",
    ),
)

LEGACY_PRICES = {
    "Manchester United Home Jersey": (Decimal("89.99"), Decimal("109.99")),
    "Real Madrid Home Jersey": (Decimal("89.99"), Decimal("109.99")),
    "Arsenal Home Jersey": (Decimal("84.99"), Decimal("99.99")),
    "FC Barcelona Home Jersey": (Decimal("89.99"), None),
    "Liverpool Home Jersey": (Decimal("89.99"), Decimal("109.99")),
    "Bayern Munich Home Jersey": (Decimal("84.99"), None),
    "Inter Milan Home Jersey": (Decimal("79.99"), Decimal("99.99")),
    "Paris Saint-Germain Home Jersey": (Decimal("89.99"), None),
    "Chelsea Home Jersey": (Decimal("89.99"), None),
}
