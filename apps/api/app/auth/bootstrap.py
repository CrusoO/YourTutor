"""First-admin bootstrap: `python -m app.auth.bootstrap admin-code EMAIL`.

Makes the admin account (or gives an existing admin a fresh code) and prints a one-time sign-in
code, so a install with no email service can still get its first admin in. Refuses an address that
already belongs to another kind of account. The code is printed once and never stored in plain text.
"""

from __future__ import annotations

import sys
import uuid

from sqlalchemy import select

from app.auth.security import now_utc
from app.auth.service import issue_signin_code
from app.db.models import UserRow
from app.db.session import session_factory

TTL_SECONDS = 900


def admin_code(email: str) -> int:
    address = email.strip().lower()
    if "@" not in address:
        print("that is not an email address", file=sys.stderr)
        return 2
    with session_factory()() as session:
        user = session.scalar(select(UserRow).where(UserRow.email == address))
        if user is not None and user.role != "admin":
            print(
                f"{address} already belongs to a {user.role} account; use another", file=sys.stderr
            )
            return 1
        if user is not None and user.suspended_at is not None:
            print("that admin account is suspended", file=sys.stderr)
            return 1
        if user is None:
            session.add(
                UserRow(
                    id=uuid.uuid4(), role="admin", email=address, locale="en", created_at=now_utc()
                )
            )
        code, _ = issue_signin_code(session, address, TTL_SECONDS)
        session.commit()
    print(f"Sign-in code for {address} (works once, 15 minutes): {code}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 2 or args[0] != "admin-code":
        print("usage: python -m app.auth.bootstrap admin-code EMAIL", file=sys.stderr)
        return 2
    return admin_code(args[1])


if __name__ == "__main__":
    raise SystemExit(main())
