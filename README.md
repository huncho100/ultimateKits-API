# Ultimate Kits API

FastAPI backend for Ultimate Kits.

## Store administration

The frontend `/admin` interface uses the existing admin role and protected product
and order operations. For endpoint definitions, report semantics, safe local
admin provisioning, migration-history cautions and production limitations, see
[Store management](docs/admin-management.md).

## Development

Copy `.env.example` to `.env`, set the database, JWT, Paystack, and SMTP
credentials, then start PostgreSQL and the API:

```powershell
docker compose up -d db
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Run the portable SQLite test suite with:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

SMTP settings are required for password reset emails. The frontend URL is
used to build the reset link.

## Product catalog and filters

`GET /products` returns the complete catalog as a JSON array, newest ID
first, without pagination or a default stock filter. Optional `sport`,
`category`, `team`, and `league` query parameters are exact matches,
case-insensitive and ignoring surrounding spaces. Multiple filters are
combined with AND. Empty or whitespace-only filter values return 422.
Unknown query parameters are not supported filters.

Catalog metadata follows the existing frontend convention:

- Current club kits: `sport=Football`, `category=Jerseys`, with the club
  name in `team` and its competition in `league`.
- National team kits: `sport=Football`, `category=Jerseys`,
  `league=National Team`, with the country in `team`.
- Retro kits: `sport=Football`, `category=Retro`, with the relevant
  club/country and league. Retro national kits can belong to both collections.
- Basketball kits: `sport=Basketball`, with operator-supplied category
  and team metadata.

Examples:

```text
/products?sport=Football
/products?sport=Football&league=National%20Team
/products?sport=Football&category=Retro
/products?team=Chelsea
```

`National Teams` and `Retro` are collections, not sport values. A request
with `sport=National%20Teams` or `sport=Retro` only matches records whose
stored sport literally has that value; it does not select a collection.

The sample seed contains nine current football club jerseys, including
Chelsea, and six operator-approved Retro products. England and both Nigeria
Retro products use `league=National Team`, so each is returned by both the
National Teams and Retro collection filters without a duplicate record.
The Nigeria Retro white shirt uses
`/images/products/retro/nigeria-retro-white.jpg`. Image files in
`ultimateKits-FE/public/images/products/` are not product records and do not
populate the catalog. New seed entries require approved names, prices,
metadata, and matching root-relative image paths; filenames alone cannot
establish sellable product details.

`seed_products` skips existing products by name without updating them.
Use the existing seed workflow only after the additional catalog entries
are operator-approved. Do not change `DATABASE_URL` merely because a
collection is empty; first confirm the intended database with the operator.

Chelsea and Manchester United use their `.webp` primary photos. Apply
Alembic migrations to correct their former `.jpg` references in existing
databases. Run `seed_products` through the existing database session to
add approved missing products without also running user seeding. Alternate
photos in the image directory are not separate products: the current
catalog stores one primary image per product.

### Repairing stale local club photographs

Run from this directory, after checking the configured database target:

```powershell
.\.venv\Scripts\python.exe -m scripts.repair_club_image_paths
.\.venv\Scripts\python.exe -m scripts.repair_club_image_paths --apply
```

The first command is a dry run. Both commands refuse any target except the
configured local PostgreSQL `ultimatekits` database with `DEBUG=True`.
This is an image-only repair, not a seed or schema migration. It requires
the sibling frontend checkout and checks all replacement files before writing.
It changes only exact stale paths on matching product names, plus matching
gallery URLs if the database retains `product_images` from the catalog branch.
If a corrected alternate already exists, only its redundant broken non-primary
alias is removed to respect the gallery's unique product/URL constraint.
IDs, prices, stock, timestamps, and other product/user/order data are unchanged.
Running it again makes no changes. Valid custom images and null images are kept.

Confirmed primary repairs (paths relative to `/images/products/football/`):

| Existing product | Stale path | Correct existing photograph |
| --- | --- | --- |
| Chelsea Home Jersey | `chelsea-home.webp` | `chelsea-home-front.webp` |
| Manchester United Red Jersey - Black Shoulder Stripes | `manchester-united-home22.jpg` | `manchester-united-home11.jpg` |

The merged frontend renamed several club photographs. Every repair target is
byte-identical (same Git blob) to the photograph its stale path used to name:
`chelsea-home2.webp` is now `chelsea-home-detail.webp`,
`manchester-united-home-closeup2.webp` is now
`manchester-united-home-front.webp`, and `manchester-united-home3.webp` is now
`manchester-united-home.webp` (the primary, so that gallery alias is removed as
redundant).

The black-stripe product is **not** the white-stripe Manchester United Home
Jersey, whose `manchester-united-home.webp` primary remains unchanged.
The current seed already uses the correct Chelsea and white-stripe United
primaries; it deliberately does not add the expanded catalog's black-stripe
product on this branch.

The reconciliation script and CSV are absent on this branch. Historical
`docs/product-image-reconciliation.csv` in the frontend and
`scripts/reconcile_product_images.py` in the API describe renames that do not
match the current files. In particular, their Chelsea/United `original_path`
associations cannot safely be inverted: some currently contain photographs
of the other club. The repair uses the actual photographs, not those aliases.
It also repairs stale Chelsea detail and United gallery URLs using the
identical photographs listed above, retaining updated
gallery row IDs and ordering. No products or gallery rows are created; only
redundant broken alternates may be deleted. Conflicting primary gallery rows
abort the transaction rather than silently changing the primary or ordering.

Vite can return its HTML app shell with HTTP 200 for a missing image URL.
Verify the image content type and browser decoding, not just the status code.
The operator has authorized development-only NGN prices for reviewed distinct
designs. The complete development catalog contains 51 products across Football,
National Teams, Retro, Basketball and Baseball. National Team Retro shirts use
one `Football`/`National Team`/`Retro` record and appear on both collections.
Images alone do not create products: explicit reviewed seed identities do.
See [development catalog instructions](docs/development-catalog.md) for all
classification decisions, temporary prices, safeguards and launch procedure.

Product image files remain in `ultimateKits-FE/public/images/products/`;
product and gallery URLs stored in the database are root-relative paths under
`/images/products/`. The `product_images` table stores one primary image and
optional ordered alternates per product. `products.image` remains the
backward-compatible primary-image field. The gallery migration backfills
existing primaries and corrects the former Chelsea path.

After confirming the configured local database, apply `python -m alembic upgrade
head`, then run `python scripts/reconcile_product_images.py --apply
--development-catalog`. This inserts missing reviewed products and gallery links
without user seeding, and writes the image inventory and
[development price register](docs/development-product-prices.csv). `--apply`
without `--development-catalog` retains the smaller original seed scope.
Running without `--apply` only refreshes reports.

All product seeds require the intended local `ultimatekits` development database
and `DEBUG=True` (or isolated in-memory SQLite tests). Existing claimed product
prices, IDs, stock and metadata are not overwritten. Administrator price PATCH
requests clear the placeholder marker, including approval at the same amount.
Never use the price register as production input or run development seeds in
production. Before release, replace/approve all prices via the existing admin API
and require `python scripts/reconcile_product_images.py --check-production-prices`
to succeed. Deployment is not ready while that preflight reports placeholders.
