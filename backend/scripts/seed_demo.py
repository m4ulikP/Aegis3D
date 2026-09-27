"""CLI script to seed reproducible Aegis3D demo data for frontend integration."""

import argparse
import sys
from pathlib import Path

# Ensure backend root directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy.exc import OperationalError

from app.db.base import Base
from app.db.config import get_settings
from app.db.seed import seed_demo_data
from app.db.session import SessionLocal, engine

settings = get_settings()


def main():
    parser = argparse.ArgumentParser(description="Seed Aegis3D demo dataset for frontend REST API testing.")
    parser.add_argument(
        "--reset",
        "-r",
        action="store_true",
        help="Purge prior demo records before reseeding.",
    )
    args = parser.parse_args()

    print("=" * 65)
    print("        AEGIS3D REPRODUCIBLE DEMO DATASET SEEDER")
    print("=" * 65)
    print(f"Target Database URL: {settings.sync_database_url.split('@')[-1] if '@' in settings.sync_database_url else settings.sync_database_url}")

    try:
        # Ensure tables exist in target PostgreSQL database
        Base.metadata.create_all(bind=engine)

        db = SessionLocal()
        try:
            summary = seed_demo_data(db=db, reset=args.reset)
        finally:
            db.close()

    except OperationalError as err:
        print("\n[ERROR] Database connection failed!")
        print(f"Details: {err.orig if hasattr(err, 'orig') else err}")
        print("\nPlease verify that the target PostgreSQL server is running and accessible.")
        print("If using non-default PostgreSQL credentials or a custom host, set DATABASE_URL:")
        print("  $env:DATABASE_URL=\"postgresql+psycopg2://user:pass@host:5432/dbname\"")
        print("  python scripts/seed_demo.py")
        sys.exit(1)

    print(f"\nExecution Status:          {summary['status'].upper()}")
    print(f"Reset Performed:           {summary['reset_performed']}")
    print(f"Zones Created/Present:     {summary['zones_created']} (IDs: {summary['zone_ids']})")
    print(f"Monitoring Session ID:     {summary['session_id']}")
    print(f"Events Seeded:             {summary['events_created']}")
    print(f"Health Snapshots Created:  {summary['health_snapshots_created']}")
    print(f"Alerts Created:            {summary['alerts_created']}")

    print("\n" + "-" * 65)
    if summary["status"] == "already_seeded":
        print("Note: Demo dataset was already present. Duplicate insertion skipped.")
        print("To force clean re-seeding, run: python scripts/seed_demo.py --reset")
    else:
        print("Demo dataset successfully seeded into database.")

    print("\nAPI Inspection Endpoints:")
    print("  - GET /api/v1/zones")
    print(f"  - GET /api/v1/zones/{summary['zone_ids'][0] if summary['zone_ids'] else 1}")
    print(f"  - GET /api/v1/zones/{summary['zone_ids'][0] if summary['zone_ids'] else 1}/events")
    print(f"  - GET /api/v1/zones/{summary['zone_ids'][0] if summary['zone_ids'] else 1}/health")
    print(f"  - GET /api/v1/zones/{summary['zone_ids'][0] if summary['zone_ids'] else 1}/trend")
    print(f"  - GET /api/v1/zones/{summary['zone_ids'][0] if summary['zone_ids'] else 1}/correlation")
    print("  - GET /api/v1/alerts")
    print("  - GET /api/v1/health/summary")
    print("=" * 65)


if __name__ == "__main__":
    main()
