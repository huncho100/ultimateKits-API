# Store management

## Audit of this branch

Before this upgrade the frontend had no admin routes or dashboard components.
The backend already had:

- Active-account/JWT authentication and a database-backed `admin` role check.
- Public catalog reads and administrator-only product create, patch and delete.
- Administrator-only order list/detail and validated fulfilment transitions.
- Optional counted inventory, consumed on verified payment, without checkout reservations.
- Trusted Paystack verification/webhook settlement and immutable order price snapshots.

Missing areas were the admin interface, overview/report queries, customer projections,
paginated order search, stock-conflict handling, and a safe local provisioning procedure.
This upgrade reuses those existing rules rather than replacing checkout or payment flows.

## Starting the interface

Start the API and frontend using their normal development commands. Visit `/admin`,
or use **Store management** from an administrator's Account page. Anonymous visitors
are sent to the existing login page; the dashboard verifies `/auth/me` before
rendering protected content. The server checks the active account and current
database role on every protected request, regardless of cached browser role claims.

Use the existing configuration:

- Backend: `DATABASE_URL`, `JWT_SECRET_KEY`, Paystack settings and `FRONTEND_URL`.
- Frontend: optional `VITE_API_BASE_URL`, defaulting to `http://localhost:8000`.
- `FRONTEND_URL` must match the browser origin for CORS.
- No secret belongs in a `VITE_` variable.

No new packages, environment variables, tables or migrations are required.

### Database safety and migration history

Inspect the configured database target before running any migration or seed.
Do not print connection strings or credentials. The inspected development target
was local PostgreSQL `ultimatekits`; its revision was `b62f0d8e3c14`, newer than this
branch's migration files. Do **not** downgrade, stamp or run `alembic upgrade head`
against that database to make the histories appear to agree. Reconcile the actual
branch/migration history first. No migration or catalog seed was run for this upgrade.

On a separate fresh development database with a coherent migration history, use
the existing `python -m alembic upgrade head` procedure after confirming its target.
Never run sample user seeding as an admin provisioning mechanism.

## Secure local admin provisioning

1. Register your own account through the existing registration flow, with a unique,
   strong password. Public registration still creates only a customer.
2. Verify the intended account ID and email through a trusted local database tool.
3. From the API directory, dry-run the promotion:

   ```powershell
   .\.venv\Scripts\python.exe -m scripts.provision_admin --user-id <id> --email <email>
   ```

4. After independently confirming the account and local database target, repeat
   with `--apply`. Sign out and sign back in to refresh the cached profile.

The command refuses remote databases, non-PostgreSQL databases, any database name
other than `ultimatekits`, and non-debug operation. Both ID and email must match an
existing active account. It creates no passwords or accounts and is idempotent.
There is no public role-elevation endpoint. Production promotion must use an
independently authorized operator/DBA procedure, not this development command.

## Pages and supported operations

- **Dashboard / Reports:** real inventory counts, recent orders, total orders,
  verified orders awaiting processing, verified sales, and cancelled paid order values.
- **Products:** name/ID/team/brand/league search, sport/category/availability filters,
  paging, existing record editing and product creation. Prices are NGN major units.
  `price` is the actual selling price; `old_price` is optional compare-at metadata.
  Metadata writes omit stock fields so an old edit form cannot overwrite stock.
  Successful writes refresh the storefront catalog context in the current tab.
- **Images:** primary root-relative `/images/` URLs with supported photograph
  extensions. Remote URLs, traversal and query parameters are rejected by the API.
  Preview errors identify missing files; syntax validation cannot establish whether
  a file is deployed on a separate frontend host. Existing image URLs are not rewritten.
- **Inventory:** validated quantity and availability writes. Blank means uncounted;
  zero is unavailable; negative, fractional and out-of-range quantities are rejected.
  The update locks the same product rows used by settlement and checks the previous
  quantity/availability, returning 409 when another writer changed them. Reload and
  review instead of blindly retrying a stock conflict.
- **Orders:** paginated ID/customer/payment-reference search; order and verified-payment
  filters; customer contact information, current item names and original price snapshots;
  read-only payment attempts; legal fulfilment actions supplied by the backend.
- **Customers:** authorized, read-only customer contact/account status, order counts
  and links to that customer's orders. No password hashes or provider secret data
  are returned, and no role editing, account deletion or impersonation UI is exposed.

Available order transitions remain the existing state machine. Payment-controlled
statuses cannot be assigned by admins. Cancellation is supported only where that
state machine allows it and requires confirmation. It does **not** issue a refund
or restore inventory. Reconcile charged payments and returned goods manually.
No refund button or fake provider-verification action is provided.

## API additions and compatibility

Every `/admin/` endpoint below requires `get_current_admin`:

| Endpoint | Purpose |
| --- | --- |
| `GET /admin/overview` | Inventory/order counts, all-time sales and five recent orders |
| `GET /admin/orders/page` | `page`, `page_size` (1-100), `q`, `status`, `payment_status=verified/unverified`, `customer_id` |
| `GET /admin/customers` | `page`, `page_size` (1-100), `q` |
| `PUT /admin/inventory/{id}` | `stock_quantity`, `in_stock`, required `expected_stock_quantity` and `expected_in_stock` |

Existing `GET /admin/orders/{id}` keeps its existing fields and adds safe customer
and payment summaries, current product names, and `available_actions`. Existing
`GET /admin/orders` remains compatible. Existing product writes and
`PATCH /admin/orders/{id}` are reused. Product inputs reject unknown fields, blank
required text, unsafe image URLs and invalid stock. Explicit nulls for required
product columns return 422 rather than a database error. Order status updates
reject unexpected fields such as `payment_status`.

## Metric definitions

- Available: `in_stock=true` and quantity is positive or uncounted.
- Out of stock/unavailable: the complement of available.
- Low stock: available counted quantity from **1 through 5**, inclusive; a subset
  of available, not an additional mutually exclusive bucket.
- Uncounted: quantity is null, irrespective of availability. No quantity is invented.
- Verified payment: stored successful Paystack record with matching order/customer,
  exact order amount and `NGN` currency. Only trusted settlement writes success.
- Sales: sum of order totals for non-cancelled orders with such a payment, counted
  once per order even if multiple payment attempts succeeded.
- Cancelled verified orders: reported separately, excluded from sales. This is not
  evidence of a refund, nor is the report a ledger of net receipts or profit.
- Awaiting processing: status `paid` with a verified matching payment.
- Reports are **all time**. No daily settlement date or tax/shipping/refund figure
  is invented from missing data.

## Limitations and production checklist

- No shipping address/reference column exists. The UI explicitly says shipping
  information is unavailable; order IDs are shown instead of invented order references.
- No archive/deactivation flag exists. Availability stops sales but does not hide a
  product or delete its history. No destructive product-delete UI was added.
- Gallery tables in the inspected local database belong to a newer branch. This
  branch has no gallery model, response field or supported gallery write API.
  Gallery editing is deliberately unavailable; do not write those tables through
  an unversioned reflection shortcut.
- No automatic refunds, returns, restocking, stock reservations, revenue exports,
  role-management UI or customer editing was introduced.
- Existing orders snapshot prices and product IDs, not product names/customer
  names/shipping information. Current names are labelled accordingly.
- Reconcile migration history and deploy API/frontend together.
- Use HTTPS, a strong rotated JWT secret, production Paystack credentials/webhook
  configuration, restricted database credentials, backups and tested restore.
- Remove/rotate any previously seeded demonstration credentials; never provision
  production accounts with the sample seed's existing defaults.
- Confirm paid cancellations/refunds and inventory corrections have an operator
  process. Add durable operator audit trails and monitoring before broader staff access.
- Validate actual opening inventory; do not replace uncounted stock with guesses.
- Run the full backend tests, frontend tests and production build. Test production
  ingress SPA routing, CORS, token expiry, role revocation and provider callbacks.
- SQLite tests cover validation/arithmetic, not PostgreSQL lock contention. Exercise
  concurrent admin stock writes and payment settlement in a staging PostgreSQL
  environment before launch. The existing payment process does not reserve stock,
  so the documented oversell/manual-resolution behavior remains.

## Validation commands

```powershell
# API directory: isolated in-memory SQLite test suite
.\.venv\Scripts\python.exe -m pytest -q

# Frontend directory
npm test
npm run build
```
