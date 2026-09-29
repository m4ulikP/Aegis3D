"""Aegis3D reproducible demo dataset seeder module."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.alert import Alert
from app.models.baseline import Baseline
from app.models.enums import (
    AlertSeverity,
    AlertStatus,
    EventSeverity,
    EventSourceType,
    EventStatus,
    SessionMode,
    SessionStatus,
)
from app.models.event import Event
from app.models.health import HealthSnapshot
from app.models.monitoring_session import MonitoringSession
from app.models.zone import Zone
from app.services.health_service import HealthService

DEMO_ZONE_1_NAME = "Zone 1 - Main Deck Girder"
DEMO_ZONE_2_NAME = "Zone 2 - Substructure Pier B"
DEMO_SESSION_NAME = "Demo Structural Health Session"


def clear_demo_data(db: Session) -> Dict[str, int]:
    """
    Safely delete existing Aegis3D demo records from the database.

    Does not affect non-demo user data. Executed atomically within session transaction.
    """
    try:
        demo_zones = db.query(Zone).filter(Zone.name.in_([DEMO_ZONE_1_NAME, DEMO_ZONE_2_NAME])).all()
        demo_sessions = db.query(MonitoringSession).filter(MonitoringSession.name == DEMO_SESSION_NAME).all()

        zone_ids = [z.id for z in demo_zones]
        session_ids = [s.id for s in demo_sessions]

        deleted_counts = {
            "alerts": 0,
            "health_snapshots": 0,
            "events": 0,
            "baselines": 0,
            "sessions": 0,
            "zones": 0,
        }

        if zone_ids or session_ids:
            if zone_ids:
                deleted_counts["alerts"] = (
                    db.query(Alert).filter(Alert.zone_id.in_(zone_ids)).delete(synchronize_session=False)
                )
                deleted_counts["baselines"] = (
                    db.query(Baseline).filter(Baseline.zone_id.in_(zone_ids)).delete(synchronize_session=False)
                )

            if zone_ids or session_ids:
                snapshot_query = db.query(HealthSnapshot)
                event_query = db.query(Event)

                if zone_ids and session_ids:
                    snapshot_filter = (HealthSnapshot.zone_id.in_(zone_ids)) | (HealthSnapshot.session_id.in_(session_ids))
                    event_filter = (Event.zone_id.in_(zone_ids)) | (Event.session_id.in_(session_ids))
                elif zone_ids:
                    snapshot_filter = HealthSnapshot.zone_id.in_(zone_ids)
                    event_filter = Event.zone_id.in_(zone_ids)
                else:
                    snapshot_filter = HealthSnapshot.session_id.in_(session_ids)
                    event_filter = Event.session_id.in_(session_ids)

                deleted_counts["health_snapshots"] = snapshot_query.filter(snapshot_filter).delete(synchronize_session=False)
                deleted_counts["events"] = event_query.filter(event_filter).delete(synchronize_session=False)

            for s in demo_sessions:
                db.delete(s)
                deleted_counts["sessions"] += 1

            for z in demo_zones:
                db.delete(z)
                deleted_counts["zones"] += 1

            db.flush()

        return deleted_counts
    except Exception:
        db.rollback()
        raise


def seed_demo_data(db: Session, reset: bool = False) -> Dict[str, Any]:
    """
    Seed a reproducible Aegis3D demo monitoring dataset into the database.

    Executed atomically within the database session. On any unexpected error,
    all uncommitted changes are rolled back automatically.

    Args:
        db: Active SQLAlchemy Session.
        reset: If True, purges prior demo records before reseeding.

    Returns:
        Dict summarizing created entity counts, IDs, and seeding status.
    """
    try:
        if reset:
            clear_demo_data(db)

        # Check for existing demo zone (idempotency check)
        existing_zone1 = db.query(Zone).filter(Zone.name == DEMO_ZONE_1_NAME).first()
        if existing_zone1:
            existing_zones = db.query(Zone).filter(Zone.name.in_([DEMO_ZONE_1_NAME, DEMO_ZONE_2_NAME])).all()
            existing_session = db.query(MonitoringSession).filter(MonitoringSession.name == DEMO_SESSION_NAME).first()
            z_ids = [z.id for z in existing_zones]

            event_cnt = db.query(Event).filter(Event.zone_id.in_(z_ids)).count() if z_ids else 0
            snapshot_cnt = db.query(HealthSnapshot).filter(HealthSnapshot.zone_id.in_(z_ids)).count() if z_ids else 0
            alert_cnt = db.query(Alert).filter(Alert.zone_id.in_(z_ids)).count() if z_ids else 0

            return {
                "status": "already_seeded",
                "reset_performed": reset,
                "zones_created": len(existing_zones),
                "session_id": existing_session.id if existing_session else None,
                "events_created": event_cnt,
                "health_snapshots_created": snapshot_cnt,
                "alerts_created": alert_cnt,
                "zone_ids": z_ids,
            }

        now = datetime.now(timezone.utc)

        # 1. Create Demo Zones
        zone1 = Zone(
            name=DEMO_ZONE_1_NAME,
            floor="Level 2",
            description="Primary structural monitoring zone for main deck longitudinal girder and sensor array.",
        )
        zone2 = Zone(
            name=DEMO_ZONE_2_NAME,
            floor="Substructure",
            description="Baseline structural monitoring zone for load-bearing pier foundation.",
        )
        db.add_all([zone1, zone2])
        db.flush()

        # 2. Create Monitoring Session
        msession = MonitoringSession(
            name=DEMO_SESSION_NAME,
            mode=SessionMode.LIVE,
            status=SessionStatus.RUNNING,
            started_at=now - timedelta(hours=2),
            description="Reproducible live monitoring session for Aegis3D frontend REST integration.",
        )
        db.add(msession)
        db.flush()

        # 3. Create Baselines
        baseline1 = Baseline(
            zone_id=zone1.id,
            mean_magnitude=1.20,
            std_magnitude=0.15,
            mean_energy=12.00,
            std_energy=1.50,
            normal_event_rate=0.02,
            valid_from=now - timedelta(days=30),
        )
        baseline2 = Baseline(
            zone_id=zone2.id,
            mean_magnitude=0.85,
            std_magnitude=0.10,
            mean_energy=8.50,
            std_energy=1.00,
            normal_event_rate=0.015,
            valid_from=now - timedelta(days=30),
        )
        db.add_all([baseline1, baseline2])
        db.flush()

        # 4. Seed Normal & Anomalous Events
        events_to_add = [
            # Zone 1 - Normal Historical Events
            Event(
                session_id=msession.id,
                zone_id=zone1.id,
                source_type=EventSourceType.SENSOR,
                source_id="PZT-Z01",
                timestamp=now - timedelta(minutes=90),
                magnitude=1.18,
                energy=11.8,
                duration_ms=45.0,
                frequency_hz=150000.0,
                severity=EventSeverity.LOW,
                status=EventStatus.DETECTED,
            ),
            Event(
                session_id=msession.id,
                zone_id=zone1.id,
                source_type=EventSourceType.SENSOR,
                source_id="PZT-Z02",
                timestamp=now - timedelta(minutes=75),
                magnitude=1.22,
                energy=12.3,
                duration_ms=42.0,
                frequency_hz=152000.0,
                severity=EventSeverity.LOW,
                status=EventStatus.DETECTED,
            ),
            Event(
                session_id=msession.id,
                zone_id=zone1.id,
                source_type=EventSourceType.SENSOR,
                source_id="PZT-Z01",
                timestamp=now - timedelta(minutes=60),
                magnitude=1.15,
                energy=11.2,
                duration_ms=40.0,
                frequency_hz=148000.0,
                severity=EventSeverity.LOW,
                status=EventStatus.DETECTED,
            ),
            Event(
                session_id=msession.id,
                zone_id=zone1.id,
                source_type=EventSourceType.SENSOR,
                source_id="PZT-Z02",
                timestamp=now - timedelta(minutes=45),
                magnitude=1.24,
                energy=12.5,
                duration_ms=47.0,
                frequency_hz=151000.0,
                severity=EventSeverity.LOW,
                status=EventStatus.DETECTED,
            ),
            # Zone 1 - Anomalous Events (Anomaly, 2-PZT Correlation, Temporal Persistence, and Increasing Trend)
            Event(
                session_id=msession.id,
                zone_id=zone1.id,
                source_type=EventSourceType.SENSOR,
                source_id="PZT-Z01",
                correlation_id="CORR-DEMO-001",
                timestamp=now - timedelta(minutes=8),
                magnitude=2.45,
                energy=25.0,
                duration_ms=120.0,
                frequency_hz=320000.0,
                severity=EventSeverity.HIGH,
                status=EventStatus.DETECTED,
            ),
            Event(
                session_id=msession.id,
                zone_id=zone1.id,
                source_type=EventSourceType.SENSOR,
                source_id="PZT-Z02",
                correlation_id="CORR-DEMO-001",
                timestamp=now - timedelta(minutes=8) + timedelta(milliseconds=15),
                magnitude=2.60,
                energy=27.5,
                duration_ms=135.0,
                frequency_hz=315000.0,
                severity=EventSeverity.HIGH,
                status=EventStatus.DETECTED,
            ),
            Event(
                session_id=msession.id,
                zone_id=zone1.id,
                source_type=EventSourceType.SENSOR,
                source_id="PZT-Z01",
                correlation_id="CORR-DEMO-002",
                timestamp=now - timedelta(minutes=5),
                magnitude=2.80,
                energy=29.0,
                duration_ms=140.0,
                frequency_hz=330000.0,
                severity=EventSeverity.CRITICAL,
                status=EventStatus.DETECTED,
            ),
            Event(
                session_id=msession.id,
                zone_id=zone1.id,
                source_type=EventSourceType.SENSOR,
                source_id="PZT-Z02",
                correlation_id="CORR-DEMO-002",
                timestamp=now - timedelta(minutes=3),
                magnitude=2.75,
                energy=28.2,
                duration_ms=130.0,
                frequency_hz=325000.0,
                severity=EventSeverity.CRITICAL,
                status=EventStatus.DETECTED,
            ),
            # Zone 2 - Normal Events
            Event(
                session_id=msession.id,
                zone_id=zone2.id,
                source_type=EventSourceType.SENSOR,
                source_id="PZT-Z07",
                timestamp=now - timedelta(minutes=30),
                magnitude=0.84,
                energy=8.4,
                duration_ms=35.0,
                frequency_hz=120000.0,
                severity=EventSeverity.LOW,
                status=EventStatus.DETECTED,
            ),
            Event(
                session_id=msession.id,
                zone_id=zone2.id,
                source_type=EventSourceType.SENSOR,
                source_id="PZT-Z08",
                timestamp=now - timedelta(minutes=10),
                magnitude=0.86,
                energy=8.6,
                duration_ms=38.0,
                frequency_hz=122000.0,
                severity=EventSeverity.LOW,
                status=EventStatus.DETECTED,
            ),
        ]

        db.add_all(events_to_add)
        db.flush()

        # 5. Evaluate Health Snapshots via HealthService
        health_service = HealthService(db)
        health_service.evaluate_zone_health(
            zone_id=zone1.id,
            session_id=msession.id,
            reference_time=now,
            window_duration_seconds=3600.0,
            persist_snapshot=True,
        )
        health_service.evaluate_zone_health(
            zone_id=zone2.id,
            session_id=msession.id,
            reference_time=now,
            window_duration_seconds=3600.0,
            persist_snapshot=True,
        )

        # 6. Create Demo Alert for Zone 1
        zone1_snapshot = (
            db.query(HealthSnapshot)
            .filter(HealthSnapshot.zone_id == zone1.id)
            .order_by(HealthSnapshot.timestamp.desc())
            .first()
        )

        alert_created = False
        if zone1_snapshot:
            alert1 = Alert(
                health_snapshot_id=zone1_snapshot.id,
                zone_id=zone1.id,
                timestamp=now - timedelta(minutes=3),
                severity=AlertSeverity.HIGH,
                title="Cross-Sensor Structural Anomaly Cluster",
                message="Multiple high-energy acoustic emission anomalies correlated across sensors PZT-Z01 and PZT-Z02 in Zone 1.",
                status=AlertStatus.ACTIVE,
            )
            db.add(alert1)
            alert_created = True

        db.commit()

        return {
            "status": "created",
            "reset_performed": reset,
            "zones_created": 2,
            "session_id": msession.id,
            "events_created": len(events_to_add),
            "health_snapshots_created": 2,
            "alerts_created": 1 if alert_created else 0,
            "zone_ids": [zone1.id, zone2.id],
        }
    except Exception:
        db.rollback()
        raise
