import argparse
import os
import sys
from pathlib import Path

from sqlalchemy import text

# Ensure project root on sys.path and isolate to E2E environment BEFORE importing backend modules
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ["ENV_FILE"] = str(PROJECT_ROOT / "backend" / ".env.e2e")
os.environ.setdefault("DATABASE_URL", "sqlite:///./outreach_e2e.db")
os.environ["DISPATCH_MODE"] = "SANDBOX"
os.environ["GEMINI_API_KEY"] = ""
os.environ["OPENAI_API_KEY"] = ""
os.environ["X_BEARER_TOKEN"] = ""

from backend.app.core.database import Base, SessionLocal, engine
from backend.app.core.security import (
    DEFAULT_PARTNER_EMAIL,
    DEFAULT_PARTNER_NAME,
    DEFAULT_PARTNER_PASSWORD,
    hash_password,
)
from backend.app.models.candidate import Candidate
from backend.app.models.ledger import OutreachLedger
from backend.app.models.queue import JobQueue
from backend.app.models.user import User
from backend.app.services.ingestion import ingest_seed_pack, seed_history_ledger
from backend.app.services.queue_worker import process_pending_jobs


def reset_e2e_database(preset: str = "CLEAN_EMPTY") -> None:
    """
    Reset outreach_e2e.db cleanly without unlinking open SQLite handles on Windows.
    Supports CLEAN_EMPTY (users only) and SEED_PACK_EVALUATED (history + 20 profiles evaluated).
    """
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        db.execute(text("PRAGMA busy_timeout = 5000"))
        # Delete in strict FK child -> parent order
        db.query(JobQueue).delete()
        db.query(OutreachLedger).delete()
        db.query(Candidate).delete()
        db.query(User).delete()
        try:
            db.execute(text("DELETE FROM sqlite_sequence"))
        except Exception:
            pass
        db.commit()

        # Seed deterministic Partner & Analyst accounts
        partner = User(
            email=DEFAULT_PARTNER_EMAIL,
            full_name=DEFAULT_PARTNER_NAME,
            password_hash=hash_password(DEFAULT_PARTNER_PASSWORD),
            role="partner",
        )
        analyst = User(
            email="analyst@xscout.local",
            full_name="X-Scout AI Scouting Analyst",
            password_hash=hash_password("Analyst2026!"),
            role="analyst",
        )
        db.add_all([partner, analyst])
        db.commit()

        if preset == "SEED_PACK_EVALUATED":
            history_csv = PROJECT_ROOT / "genai-outreach-pack" / "outreach_history_log.csv"
            seed_history_ledger(db, history_csv)
            ingest_seed_pack(db)
            process_pending_jobs(db, job_type="AI_EVALUATE", limit=100)
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reset & seed isolated outreach_e2e.db")
    parser.add_argument(
        "--preset",
        choices=["CLEAN_EMPTY", "SEED_PACK_EVALUATED"],
        default="CLEAN_EMPTY",
        help="Target isolated E2E data preset",
    )
    args = parser.parse_args()
    reset_e2e_database(preset=args.preset)
    print(f"[e2e_seed] Reset outreach_e2e.db to preset={args.preset}")

