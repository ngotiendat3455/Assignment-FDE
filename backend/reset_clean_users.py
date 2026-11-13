"""
Clean User-Only Database Reset Tool (Sub-task 7.1).

Wipes all operational outreach data (`job_queue`, `outreach_ledger`, `candidates`)
while preserving login accounts in `users` (guaranteeing the default Partner user).

Usage:
    python -m backend.reset_clean_users --yes
    python -m backend.reset_clean_users --yes --with-analyst
    ENV_FILE=backend/.env python -m backend.reset_clean_users --yes --purge-extra-users
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, Any, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

# Ensure project root is importable when run as script or module
_backend_dir = Path(__file__).resolve().parent
_project_root = _backend_dir.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from backend.app.core.config import settings
from backend.app.core.database import Base, engine as default_engine, SessionLocal as DefaultSessionLocal
from backend.app.core.security import (
    DEFAULT_PARTNER_EMAIL,
    ensure_default_partner_user,
    hash_password,
)
from backend.app.models.candidate import Candidate
from backend.app.models.ledger import OutreachLedger
from backend.app.models.queue import JobQueue
from backend.app.models.user import User

DEFAULT_ANALYST_EMAIL = "analyst@genaifund.ai"
DEFAULT_ANALYST_PASSWORD = "Analyst2026!"


def _ensure_analyst_user(db: Session) -> User:
    user = db.query(User).filter(User.email == DEFAULT_ANALYST_EMAIL).first()
    if not user:
        user = User(
            email=DEFAULT_ANALYST_EMAIL,
            full_name="GenAI Fund Analyst",
            password_hash=hash_password(DEFAULT_ANALYST_PASSWORD),
            role="analyst",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def reset_database_keep_users(
    db: Session,
    with_analyst: bool = False,
    purge_extra_users: bool = False,
) -> Dict[str, Any]:
    """Delete candidates, outreach_ledger, and job_queue while keeping user accounts."""
    deleted_jobs = db.query(JobQueue).delete(synchronize_session=False)
    deleted_ledger = db.query(OutreachLedger).delete(synchronize_session=False)
    deleted_candidates = db.query(Candidate).delete(synchronize_session=False)

    # Reset SQLite autoincrement counters when applicable
    bind = db.get_bind()
    if bind is not None and bind.dialect.name == "sqlite":
        has_seq = db.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='sqlite_sequence'")
        ).first()
        if has_seq:
            for table_name in ("job_queue", "outreach_ledger", "candidates"):
                db.execute(text("DELETE FROM sqlite_sequence WHERE name = :t"), {"t": table_name})

    db.commit()
    db.expire_all()

    if purge_extra_users:
        keep_emails = {DEFAULT_PARTNER_EMAIL}
        if with_analyst:
            keep_emails.add(DEFAULT_ANALYST_EMAIL)
        db.query(User).filter(~User.email.in_(keep_emails)).delete(synchronize_session=False)
        db.commit()
        db.expire_all()

    ensure_default_partner_user(db)
    if with_analyst:
        _ensure_analyst_user(db)

    retained_users = [
        {"email": u.email, "role": u.role, "full_name": u.full_name}
        for u in db.query(User).order_by(User.id.asc()).all()
    ]

    return {
        "deleted": {
            "job_queue": deleted_jobs,
            "outreach_ledger": deleted_ledger,
            "candidates": deleted_candidates,
        },
        "remaining": {
            "users": len(retained_users),
            "candidates": db.query(Candidate).count(),
            "outreach_ledger": db.query(OutreachLedger).count(),
            "job_queue": db.query(JobQueue).count(),
        },
        "retained_users": retained_users,
    }


def _open_session(db_url: Optional[str]) -> tuple[Session, str]:
    if not db_url:
        Base.metadata.create_all(bind=default_engine)
        return DefaultSessionLocal(), settings.DATABASE_URL

    connect_args = {"check_same_thread": False} if "sqlite" in db_url else {}
    custom_engine = create_engine(db_url, connect_args=connect_args, echo=False)
    Base.metadata.create_all(bind=custom_engine)
    CustomSession = sessionmaker(autocommit=False, autoflush=False, bind=custom_engine)
    return CustomSession(), db_url


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Reset database operational tables while keeping user login accounts."
    )
    parser.add_argument(
        "--yes",
        "-y",
        "--confirm",
        action="store_true",
        help="Skip interactive confirmation prompt.",
    )
    parser.add_argument(
        "--with-analyst",
        action="store_true",
        help="Also ensure analyst@genaifund.ai (role=analyst) exists for RBAC testing.",
    )
    parser.add_argument(
        "--purge-extra-users",
        action="store_true",
        help="Remove user accounts other than partner (and analyst if --with-analyst is set).",
    )
    parser.add_argument(
        "--db-url",
        default=None,
        help="Override DATABASE_URL target (defaults to configured settings.DATABASE_URL).",
    )
    args = parser.parse_args(argv)

    target_url = args.db_url or settings.DATABASE_URL
    if not args.yes:
        reply = input(
            f"Reset all candidates/ledger/jobs in [{target_url}] and keep only users? [y/N]: "
        ).strip().lower()
        if reply not in ("y", "yes"):
            print("Aborted cleanly. No data modified.")
            return 1

    db, resolved_url = _open_session(args.db_url)
    try:
        summary = reset_database_keep_users(
            db,
            with_analyst=args.with_analyst,
            purge_extra_users=args.purge_extra_users,
        )
    finally:
        db.close()

    user_list = ", ".join(f"{u['email']} [role={u['role']}]" for u in summary["retained_users"])
    rem = summary["remaining"]
    print("=" * 70)
    print("[CLEAN USER-ONLY RESET COMPLETE]")
    print(f"• Database:        {resolved_url}")
    print(f"• Users retained:  {rem['users']} ({user_list})")
    print(f"• Candidates:      {rem['candidates']}")
    print(f"• OutreachLedger:  {rem['outreach_ledger']}")
    print(f"• JobQueue:        {rem['job_queue']}")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
