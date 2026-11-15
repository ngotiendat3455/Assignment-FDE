import sys
from pathlib import Path

# Add project root to path
backend_dir = Path(__file__).resolve().parent
project_root = backend_dir.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.app.core.database import engine, Base, SessionLocal
from backend.app.core.security import hash_password
from backend.app.models.user import User
from backend.app.models.candidate import Candidate
from backend.app.models.ledger import OutreachLedger
from backend.app.services.ingestion import (
    seed_history_ledger,
    parse_csv_content,
    ingest_candidate_batch,
)
from backend.app.services.queue_worker import process_pending_jobs


def seed_database():
    print("=" * 70)
    print("⚡ INITIALIZING X-SCOUT AI OUTREACH DATABASE")
    print("=" * 70)

    # 1. Create tables
    print("--> Creating database tables (SQLite with WAL mode)...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # 2. Seed Default Partner User
        partner_email = "partner@xscout.local"
        existing_partner = db.query(User).filter(User.email == partner_email).first()
        if not existing_partner:
            print(f"--> Seeding default Partner user: {partner_email}...")
            partner_user = User(
                email=partner_email,
                full_name="X-Scout AI Investment Partner",
                password_hash=hash_password("XScout2026!"),
                role="partner",
            )
            db.add(partner_user)
            db.commit()
            print("    [OK] Partner user created (Password: XScout2026!)")
        else:
            print(f"    [INFO] Partner user already exists: {partner_email}")

        # 3. Seed Historical Outreach Ledger
        history_csv = project_root / "genai-outreach-pack" / "outreach_history_log.csv"
        if history_csv.exists():
            print(f"--> Seeding historical outreach ledger from: {history_csv.name}...")
            hist_count = seed_history_ledger(db, history_csv)
            print(f"    [OK] Seeded {hist_count} historical outreach records.")
        else:
            print(f"    [WARN] Historical outreach CSV not found at {history_csv}")

        # 4. Ingest 20 Candidate Profiles from candidates_seed.csv
        seed_csv = project_root / "genai-outreach-pack" / "candidates_seed.csv"
        if seed_csv.exists():
            print(f"--> Ingesting candidate profiles from: {seed_csv.name}...")
            with open(seed_csv, mode="r", encoding="utf-8") as f:
                parsed_records = parse_csv_content(f.read())
            report = ingest_candidate_batch(db, parsed_records, source_label="SEED_PACK")
            print(f"    [OK] Ingestion Complete:")
            print(f"         - Total rows parsed: {report['total_rows']}")
            print(f"         - Newly imported: {report['imported']}")
            print(f"         - In-batch duplicates skipped: {report['in_batch_duplicates_skipped']}")
            print(f"         - Already in DB skipped: {report['already_in_db_skipped']}")
            print(f"         - Flagged as already contacted in ledger: {report['already_contacted_in_ledger']}")

            print("--> Running Queue 1 (Tri-Guard AI Evaluation Engine) on queued profiles...")
            ai_report = process_pending_jobs(db, job_type="AI_EVALUATE")
            print(f"    [OK] AI Evaluation Complete: {ai_report['ai_evaluated']} profiles evaluated.")
        else:
            print(f"    [WARN] Candidates seed CSV not found at {seed_csv}")

        # Summary
        total_candidates = db.query(Candidate).count()
        total_ledger = db.query(OutreachLedger).count()
        total_users = db.query(User).count()

        print("-" * 70)
        print(f"DATABASE SUMMARY:")
        print(f"• Total Users:            {total_users}")
        print(f"• Total Candidates:       {total_candidates}")
        print(f"• Total Ledger Records:   {total_ledger}")
        print("=" * 70)
        print("SUCCESS: Database successfully initialized and seeded!")
        print("=" * 70)

    finally:
        db.close()


if __name__ == "__main__":
    seed_database()

