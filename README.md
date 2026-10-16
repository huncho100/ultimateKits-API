# Ultimate Kits API

FastAPI backend for Ultimate Kits.

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
