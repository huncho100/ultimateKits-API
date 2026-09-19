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
