# Development catalog and production price replacement

## Authorization and source of truth

This catalog is for development and storefront testing, not a production
price approval. All amounts are NGN `Decimal` values with two decimal places.
Do not convert the former sample amounts as foreign currency.

- **Live selling prices:** `products.price` and `products.old_price` in the
  configured database. The API, cart and orders read these records.
- **Development-only seed definitions:** the existing 15 entries in
  [seed.py](../app/database/seed.py) and the 36 reviewed additions in
  [development_catalog.py](../app/database/development_catalog.py).
- **Price provenance:** `products.development_placeholder`. It is returned
  by the product API and mapped to storefront labels and a development banner.
- **Stable seed identity:** unique, nullable `products.catalog_key`. Existing
  IDs are preserved. Name/image lookup only adopts unclaimed existing records;
  conflicting identities stop the seed rather than create duplicates.
- **Price register:** [development-product-prices.csv](development-product-prices.csv)
  is a generated, product-by-product audit OUTPUT containing IDs, keys, currency,
  temporary/current prices and placeholder status. It is never read by the seed
  or used as a production pricing mechanism. Editing it changes no price.
- There is no product management admin UI in this repository. The existing
  administrator-protected `POST /products` and `PATCH /products/{id}` API routes
  control published records.

## Deterministic temporary prices

The nine historical club samples and all new Football designs use 25000.00;
Basketball designs use 20000.00; Baseball designs use 22500.00. These explicit
sport-to-price mappings are development defaults, all within 15000.00–35000.00.
The same stable identity always receives the same initial amount.

The six explicitly approved Retro products retain 25000.00 and are **not**
marked as placeholders. In the original local database, the following known
sample amounts are replaced once, only while identity is unclaimed and name,
image, selling price and old-price pair still match the historical seed:

| Existing product | Former sample price | Former old price | Development NGN price |
| --- | ---: | ---: | ---: |
| Manchester United Home Jersey | 89.99 | 109.99 | 25000.00 |
| Real Madrid Home Jersey | 89.99 | 109.99 | 25000.00 |
| Arsenal Home Jersey | 84.99 | 99.99 | 25000.00 |
| FC Barcelona Home Jersey | 89.99 | null | 25000.00 |
| Liverpool Home Jersey | 89.99 | 109.99 | 25000.00 |
| Bayern Munich Home Jersey | 84.99 | null | 25000.00 |
| Inter Milan Home Jersey | 79.99 | 99.99 | 25000.00 |
| Paris Saint-Germain Home Jersey | 89.99 | null | 25000.00 |
| Chelsea Home Jersey | 89.99 | null | 25000.00 |

The old sample discounts are cleared, not converted into invented production
promotions. All other existing prices and stock settings are preserved.
Seeding never changes prices of claimed identities, including a placeholder
that has subsequently been approved at exactly the same amount.

## Classification and gallery decisions

All files remain under frontend `public/images/products/`; database image and
gallery URLs remain `/images/products/...`. No upload endpoint or external
hosting is involved. No images are moved into `src/assets`.

- One product per design, with alternate views linked in primary-first order.
  Germany away, Celtics black, Nigeria light green, Nigeria flame, and Portugal
  home have reviewed alternate photographs. The Manchester United `home-33`
  filename is an alternate of the existing collared shirt, not a visible No. 33
  product. `home11` depicts a distinct black-shoulder-stripe design.
- The backend has no product option/personalization model. Its cart/order lines
  identify product ID, not player printing. Clearly visible fixed numbered
  shirts therefore receive separately named `No. N` listings. A front/back
  composite of the **same item** remains one listing. This does not offer
  custom printing or infer player identity.
- Brazil's unnumbered away shirt and visibly pre-printed No. 7 are separate
  listings, not alternate views. Argentina home/away remain separate designs;
  the combined photograph is not a new bundle.
- Nigeria Classic Green/White No. 22 uses the actual `nigeria-1996.jpg` file;
  its previously approved Retro classification and printing are retained,
  without claiming the filename's year. It appears on National Teams and Retro
  through one record (`Football`, `National Team`, `Retro`).
- `nigeria-home`, `nigeria-white` and `nigeria-white2` are one flame design.
  `nigeria-white3` is a separate plain white design. `nigeria-nike` depicts a
  separate black/green brush pattern, not a flame alternate. `nigeria-green`
  and `nigeria-green2` have different designs. The `women` filename alone does
  not establish fit/gender, so the matching light-green front/back photo is
  attached without a gender claim.
- Generic-folder Dallas, Heat and Rockets images and Retro-folder
  `nigeria-white` duplicate existing files byte-for-byte. SHA-256 duplicate
  detection preserves them on disk but does not add redundant products/gallery
  rows.
- Generic Spurs is a visibly black/grey Basketball shirt despite its filename.
  Generic Yankees black No. 99, pinstripe No. 22, and New York grey baseball
  designs are applicable distinct products. The grey shirt is not assigned an
  unverified franchise.
- Five uncertain photographs remain unmatched: Haaland/Manchester City,
  James/Chelsea (different central badge), Haaland/Norway, Lamine Yamal/Spain,
  and the Argentina two-shirt composite. Exact reasons are per-file in
  [the reconciliation report](../../ultimateKits-FE/docs/product-image-reconciliation.csv).
  No seasons, editions, licensing, descriptions or ratings are fabricated.
- New development products use `in_stock=true`, `stock_quantity=null` so existing
  uncounted-stock behavior supports storefront testing. This is **not** a claim
  of measured physical inventory; set actual stock before launch.

## Safe local execution

From the API directory, with the existing virtual environment and configuration:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe scripts\reconcile_product_images.py --apply --development-catalog
.\.venv\Scripts\python.exe scripts\reconcile_product_images.py --apply --development-catalog
```

Inspect the configured target before migration. Writes require `DEBUG=True`
and the configured PostgreSQL database `ultimatekits` on localhost/127.0.0.1/::1.
The seed also allows isolated in-memory SQLite tests, not file-based SQLite.
Neither the command nor any seed helper changes `DATABASE_URL`. Product seed
functions reject production/remote/wrong-database targets. The reconciliation
command requires the Alembic head before writing and checks every configured
image file. Image failures roll back the catalog transaction.

This path runs product/gallery seeding only: no user seeding, deletes, order,
cart, payment or review updates. Repeated runs preserve IDs, approved prices,
edited metadata/stock, and existing gallery row IDs. An existing seed cannot
silently reset an operator price. A new design is insert-only.

Expected complete local result: 51 products, 65 linked photographs (51 primary
and 14 alternates), 4 preserved duplicate files, 5 unmatched files. Collections
overlap: Football 37, Clubs 14, National Teams 23, Retro 7, Basketball 11,
Baseball 3. Six approved Retro prices plus 45 development placeholders.
Basketball has `/basketball`; Baseball is available through the Products sport
filter. National Teams and Retro remain their existing routes.

## Exact production price-update procedure

1. Back up the database. Review every row of the generated price register for
   identity/ID, but obtain real NGN selling prices independently from the
   operator. **Do not edit or import the development register as production
   pricing data.** Review real stock and any old-price promotions separately.
2. Sign in as an existing administrator through the existing authentication
   flow. For each placeholder ID, update the **live product record** through
   `PATCH /products/{id}`. Use the same route even when approving the current
   amount unchanged; supplying a valid price automatically clears
   `development_placeholder`. Non-price edits do not clear it. Clients cannot
   directly set the placeholder flag or the seed identity.

   Example only (replace ID and amount with the actual approval):

   ```powershell
   $headers = @{ Authorization = "Bearer $env:ULTIMATEKITS_ADMIN_TOKEN" }
   Invoke-RestMethod -Method Patch -Uri "http://localhost:8000/products/16" `
     -Headers $headers -ContentType "application/json" `
     -Body '{"price":"28000.00","old_price":null}'
   ```

   Do not put currency symbols, commas or formatted amounts in numeric fields.
   Direct SQL is not necessary. If used operationally instead, both the numeric
   `price` and `development_placeholder=false` must be changed in a transaction;
   preserving `catalog_key` prevents seed re-adoption.
3. Refresh the audit output without any database writes:

   ```powershell
   .\.venv\Scripts\python.exe scripts\reconcile_product_images.py
   ```

4. Run this read-only deployment preflight as a required release step:

   ```powershell
   .\.venv\Scripts\python.exe scripts\reconcile_product_images.py --check-production-prices
   ```

   A nonzero exit means **do not deploy**: it lists every remaining placeholder
   ID. It succeeds only after all placeholders are replaced/explicitly approved.
   No production deployment pipeline is present in this repository; wire this
   command into the release process before enabling production traffic.
5. For a fresh production database, apply migrations and publish only
   operator-approved entries using administrator `POST /products`, or restore
   the reviewed database. **Never run development/sample seed commands in
   production.** Set `DEBUG=False`. The seeds refuse to run in that mode and
   never read the price register.
6. Rebuild/reload the storefront after approval and confirm prices/stock.
   The development labels disappear when the API no longer returns placeholders.
   Existing order unit-price snapshots are not rewritten by catalog price
   updates. Existing carts continue to use the established backend repricing
   behavior; no order or payment logic is modified here.

## Verified implementation result - 2026-10-15

- Applied Alembic `b62f0d8e3c14` after confirming the configured local target;
  previous revision was `a52c7e9d4b61`. `alembic check` reports no schema drift.
- Created 36 products and replaced 9 recognized legacy sample price pairs.
  Preserved original product IDs 1–15, their names and primary images, and the
  six explicitly approved prices. PostgreSQL sequence gaps are not renumbered.
- Gallery associations increased from 22 to 65: 43 additions, with no deletions.
  The second full seed created 0 products, changed 0 prices, and added 0 images.
- SHA-256 snapshots of **all row values** in users (44), carts (3), cart_items
  (6), orders (9), order_items (24), and payments (11) matched before/after.
  There is no review table in the current schema.
- Complete backend suite: **333 passed**. After the final same-price approval
  regression addition, the targeted catalog suites also passed **36 tests**.
  Existing warnings concern the Starlette test client and short development
  JWT test key; neither authentication nor payment behavior was changed.
- Frontend: **22 tests passed**, typecheck and production build passed.
  All 74 public image files are present byte-for-byte in the build.
- Live API verified: full array 51; Football 37; National Team league 23; Retro
  category 7; Basketball 11; Baseball 3. All 65 gallery URLs returned HTTP 200
  with image content and decoded successfully in a browser.
- Browser rendered National Teams 23/23, Retro 7/7, Basketball 11/11, Clubs
  14/14, and Products 51/51, without broken/placeholder photographs. Germany,
  Nigeria flame, Celtics and Manchester United gallery selections loaded.
  Search returned 8 Nigeria products; ascending/descending price sorting worked.
  Simulated empty response and HTTP 503 produced the correct states, and retry
  recovered all 23 National Teams products. These simulations did not write data.
- Production-price preflight deliberately exits nonzero while the 45 authorized
  development placeholders remain. Production pricing/stock approval remains
  an operator release task, not a failed development catalog seed.

### Complete changed-file manifest

Paths below are relative to the API documentation folder. No image binaries were
renamed, deleted or modified during this development-price implementation.

| File | Purpose |
| --- | --- |
| [development_catalog.py](../app/database/development_catalog.py) | Reviewed distinct designs, alternate associations, stable keys, deterministic prices, local-development guard. |
| [seed.py](../app/database/seed.py) | Idempotent insert/adoption, protected price reconciliation, primary/gallery seeding. |
| [product.py model](../app/models/product.py) | Unique catalog identity and placeholder provenance. |
| [product.py schemas](../app/schemas/product.py) | Expose provenance; reject null price updates. |
| [product_service.py](../app/services/product_service.py) | Clear placeholder on authenticated price approval, including unchanged amounts. |
| [b62f0d8e3c14 migration](../alembic/versions/b62f0d8e3c14_add_catalog_identity_and_development_price_flag.py) | Add identity/provenance without repricing existing records. |
| [reconcile_product_images.py](../scripts/reconcile_product_images.py) | Guarded complete seed, head/image checks, duplicate report, price register, release preflight. |
| [test_development_catalog.py](../tests/test_development_catalog.py) | Complete counts, prices, identity, idempotency, production guards, admin approval, migration and register tests. |
| [test_product_catalog.py](../tests/test_product_catalog.py) | Update expected alternate count for the visually matched collared Manchester United photo. |
| [test_product_image_reconciliation.py](../tests/test_product_image_reconciliation.py) | Verify all 74 files, 65 associations, 4 duplicates and 5 unmatched files. |
| [README.md](../README.md) | Entry-point commands and production pricing safeguards. |
| [development-catalog.md](development-catalog.md) | Updated implementation instructions, classifications, exact launch procedure and verification report. |
| [development-product-prices.csv](development-product-prices.csv) | Generated product-by-product identity/ID/price/provenance register. |
| [Product type](../../ultimateKits-FE/src/types/product.ts) | Frontend placeholder provenance field. |
| [productServices.ts](../../ultimateKits-FE/src/services/productServices.ts) | Preserve API provenance during mapping. |
| [productServices.test.ts](../../ultimateKits-FE/src/services/productServices.test.ts) | NGN amount/provenance mapping regression. |
| [ProductCard.tsx](../../ultimateKits-FE/src/components/products/ProductCard.tsx) | Label temporary card prices. |
| [ProductPrice.tsx](../../ultimateKits-FE/src/components/products/ProductPrice.tsx) | Label temporary detail prices. |
| [ProductPrice.test.tsx](../../ultimateKits-FE/src/components/products/ProductPrice.test.tsx) | Placeholder/approved display tests. |
| [ProductInfo.tsx](../../ultimateKits-FE/src/components/products/ProductInfo.tsx) | Pass price provenance to detail price display. |
| [MainLayout.tsx](../../ultimateKits-FE/src/components/layouts/MainLayout.tsx) | Store-wide development-price notice. |
| [Basketball.tsx](../../ultimateKits-FE/src/pages/Basketball.tsx) | Basketball collection using existing shared catalog UI. |
| [App.tsx](../../ultimateKits-FE/src/App.tsx) | Register Basketball route. |
| [navigation.ts](../../ultimateKits-FE/src/constants/navigation.ts) | Discoverable Basketball navigation/footer links. |
| [CatalogCollections.test.tsx](../../ultimateKits-FE/src/pages/CatalogCollections.test.tsx) | National/Retro/Basketball membership, listing search, empty/API error/retry tests. |
| [product-image-reconciliation.csv](../../ultimateKits-FE/docs/product-image-reconciliation.csv) | Refreshed complete image accounting and classification decisions. |
| [product-images.md](../../docs/product-images.md) | Update catalog authorization, gallery architecture and current file count. |
