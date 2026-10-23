"""Promote an existing active account on the confirmed local development database."""

import argparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.database import engine
from app.models.user import User


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user-id", type=int, required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    url = engine.url
    if not (
        settings.DEBUG
        and url.get_backend_name() == "postgresql"
        and url.host in {"localhost", "127.0.0.1", "::1"}
        and url.database == "ultimatekits"
    ):
        raise RuntimeError("Provisioning requires the configured local development ultimatekits database.")
    # Register model relationships without invoking any seed function.
    from app.main import app  # noqa: F401

    with Session(engine) as db:
        user = db.scalar(select(User).where(
            User.id == args.user_id, User.email == args.email, User.is_active.is_(True)
        ).with_for_update())
        if user is None:
            raise RuntimeError("No active account matches both the supplied ID and email.")
        if args.apply:
            user.role = "admin"
            db.commit()
        print("Admin role applied." if args.apply else "Account matches; dry run only. Add --apply to promote.")


if __name__ == "__main__":
    main()
