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
