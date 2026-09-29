"""Tests for the live telemetry processing SSE stream and in-process event bus."""

import asyncio
from datetime import datetime, timezone
import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.baseline import Baseline
from app.models.enums import SessionMode, SessionStatus
from app.models.monitoring_session import MonitoringSession
from app.models.zone import Zone
from app.schemas.live_telemetry import (
    LiveEventType,
    LiveProcessingEvent,
    ProcessingStage,
    STAGE_ORDER,
)
from app.schemas.telemetry import TelemetryIngestRequest
from app.services.live_bus import LiveEventBus, get_live_event_bus
from app.services.telemetry_service import TelemetryService, ZoneNotFoundError


@pytest.fixture(name="db_session")
def db_session_fixture():
    """In-memory SQLite database session fixture."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(name="client")
def client_fixture(db_session: Session):
    """FastAPI TestClient fixture with overridden get_db dependency."""
    def _get_db_override():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _get_db_override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="seeded_context")
def seeded_context_fixture(db_session: Session):
    """Seed test zone and baseline."""
    now = datetime.now(timezone.utc)
    zone = Zone(name="Zone 1 - Main Deck Girder", floor="Deck Level 1")
    db_session.add(zone)
    db_session.flush()

    baseline = Baseline(
        zone_id=zone.id,
        mean_magnitude=1.5,
        std_magnitude=0.3,
        mean_energy=2.0,
        std_energy=0.4,
        normal_event_rate=0.05,
        valid_from=now,
    )
    db_session.add(baseline)

    session = MonitoringSession(
        name="Live Test Session",
        mode=SessionMode.LIVE,
        status=SessionStatus.RUNNING,
        started_at=now,
    )
    db_session.add(session)
    db_session.commit()
    return {"zone": zone, "baseline": baseline, "session": session}


def test_event_bus_subscribe_unsubscribe():
    """Verify subscriber queues register and unregister cleanly."""
    bus = LiveEventBus(max_queue_size=10)
    assert bus.subscriber_count == 0

    q1 = bus.subscribe()
    assert bus.subscriber_count == 1

    q2 = bus.subscribe()
    assert bus.subscriber_count == 2

    bus.unsubscribe(q1)
    assert bus.subscriber_count == 1

    bus.unsubscribe(q2)
    assert bus.subscriber_count == 0


def test_event_bus_broadcast_to_multiple_subscribers():
    """Verify published events reach all active subscribers."""
    bus = LiveEventBus(max_queue_size=10)
    q1 = bus.subscribe()
    q2 = bus.subscribe()

    event = LiveProcessingEvent(
        type=LiveEventType.PROCESSING_STARTED,
        trace_id="trace-test-01",
        sensor_id="PZT-Z01",
        status="started",
        timestamp=datetime.now(timezone.utc),
    )
    bus.publish(event)

    assert not q1.empty()
    assert not q2.empty()

    ev1 = q1.get_nowait()
    ev2 = q2.get_nowait()

    assert ev1.trace_id == "trace-test-01"
    assert ev2.trace_id == "trace-test-01"


def test_event_bus_bounded_queue_no_overflow():
    """Verify bounded queue drops oldest events without blocking or memory leak."""
    bus = LiveEventBus(max_queue_size=3)
    queue = bus.subscribe()

    for i in range(5):
        bus.publish(
            LiveProcessingEvent(
                type=LiveEventType.STAGE_COMPLETED,
                sequence=i,
                status="completed",
                timestamp=datetime.now(timezone.utc),
            )
        )

    # Queue should be bounded to 3 items, containing the most recent sequences (2, 3, 4)
    assert queue.qsize() == 3
    items = []
    while not queue.empty():
        items.append(queue.get_nowait())

    assert len(items) == 3
    assert items[0].sequence == 2
    assert items[1].sequence == 3
    assert items[2].sequence == 4


def test_pipeline_stage_ordering_on_ingest(db_session: Session, seeded_context):
    """Verify that all 9 processing stages execute in exact conceptual order and emit events."""
    bus = get_live_event_bus()
    bus.clear()
    queue = bus.subscribe()

    service = TelemetryService(db_session)
    # Exceed threshold to trigger active event detection
    samples = [0.0] * 100
    for i in range(30, 50):
        samples[i] = 4.5

    payload = TelemetryIngestRequest(
        sensor_id="PZT-Z05",
        zone_name="Zone 1 - Main Deck Girder",
        sample_rate_hz=1000.0,
        samples=samples,
        sequence=42,
        detection_threshold=1.0,
    )

    resp = service.ingest_telemetry(payload)
    assert resp.telemetry_accepted is True
    assert resp.events_detected > 0

    # Collect all emitted events from queue
    events = []
    while not queue.empty():
        events.append(queue.get_nowait())

    bus.unsubscribe(queue)

    assert len(events) >= 20  # 1 started + 9*(started+completed) + 1 completed

    # 1. First event is PROCESSING_STARTED
    assert events[0].type == LiveEventType.PROCESSING_STARTED
    assert events[0].sensor_id == "PZT-Z05"

    # 2. Check stage ordering: verify that each of the 9 stages appears in STAGE_ORDER
    stage_events = [e for e in events if e.stage is not None]
    executed_stages_started = [e.stage for e in stage_events if e.type == LiveEventType.STAGE_STARTED]
    executed_stages_completed = [e.stage for e in stage_events if e.type == LiveEventType.STAGE_COMPLETED]

    assert executed_stages_started == STAGE_ORDER
    assert executed_stages_completed == STAGE_ORDER

    # 3. Final event is PROCESSING_COMPLETED with authoritative trace_id
    assert events[-1].type == LiveEventType.PROCESSING_COMPLETED
    assert events[-1].trace_id.startswith("trace-evt-")
    assert events[-1].event_id is not None


def test_pipeline_quiet_packet_stage_emission(db_session: Session, seeded_context):
    """Verify that quiet below-threshold packets still cycle all 9 stages and complete cleanly."""
    bus = get_live_event_bus()
    bus.clear()
    queue = bus.subscribe()

    service = TelemetryService(db_session)
    # Quiet samples well below detection threshold
    samples = [0.01, -0.01, 0.02, 0.0, -0.02] * 20
    payload = TelemetryIngestRequest(
        sensor_id="PZT-Z05",
        zone_name="Zone 1 - Main Deck Girder",
        sample_rate_hz=1000.0,
        samples=samples,
        sequence=101,
        detection_threshold=1.5,
    )

    resp = service.ingest_telemetry(payload)
    assert resp.status == "PROCESSED_NO_EVENT"
    assert resp.events_detected == 0

    events = []
    while not queue.empty():
        events.append(queue.get_nowait())

    bus.unsubscribe(queue)

    assert events[0].type == LiveEventType.PROCESSING_STARTED
    assert events[-1].type == LiveEventType.PROCESSING_COMPLETED
    assert events[-1].trace_id.startswith("trace-PZT-Z05-101")


def test_pipeline_error_emission(db_session: Session):
    """Verify that a processing error (e.g. unknown zone) emits PROCESSING_ERROR."""
    bus = get_live_event_bus()
    bus.clear()
    queue = bus.subscribe()

    service = TelemetryService(db_session)
    payload = TelemetryIngestRequest(
        sensor_id="PZT-Z01",
        zone_name="Nonexistent Zone 999",
        sample_rate_hz=1000.0,
        samples=[1.0, 2.0],
        sequence=999,
    )

    with pytest.raises(ZoneNotFoundError):
        service.ingest_telemetry(payload)

    events = []
    while not queue.empty():
        events.append(queue.get_nowait())

    bus.unsubscribe(queue)

    error_events = [e for e in events if e.type == LiveEventType.PROCESSING_ERROR]
    assert len(error_events) >= 1
    assert error_events[0].stage == ProcessingStage.INGESTION
    assert "not found" in error_events[0].error_message.lower()


def test_sse_endpoint_receives_heartbeat(client: TestClient):
    """Verify that GET /api/v1/telemetry/live establishes an SSE stream and receives initial heartbeat."""
    response = client.get("/api/v1/telemetry/live?max_events=1")
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")

    text = response.text
    assert "data:" in text
    lines = [line.strip() for line in text.split("\n") if line.strip().startswith("data:")]
    assert len(lines) >= 1
    raw_json = lines[0].replace("data:", "").strip()
    data = json.loads(raw_json)
    assert data["type"] == "heartbeat"
    assert data["status"] == "connected"
