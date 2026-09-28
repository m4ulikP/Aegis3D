"""Service layer orchestrating raw sensor telemetry ingestion and signal processing pipeline."""

from datetime import datetime, timedelta, timezone
import re
from typing import List, Optional
import numpy as np
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.anomaly.exceptions import BaselineNotFoundError, InvalidEventDataError
from app.models.alert import Alert
from app.models.enums import (
    AlertSeverity,
    AlertStatus,
    EventSeverity,
    EventSourceType,
    EventStatus,
    HealthStatus,
    SessionMode,
    SessionStatus,
)
from app.models.event import Event
from app.models.health import HealthSnapshot
from app.models.monitoring_session import MonitoringSession
from app.models.zone import Zone
from app.processing import (
    ProcessedEvent,
    SampledSignal,
    process_signal_pipeline,
)
from app.repositories.baseline_repository import BaselineRepository
from app.repositories.event_repository import EventRepository
from app.schemas.telemetry import (
    ExtractedFeaturesSchema,
    TelemetryEventResult,
    TelemetryIngestRequest,
    TelemetryIngestResponse,
)
from app.services.anomaly_service import AnomalyService
from app.services.correlation_service import CorrelationService
from app.services.health_service import HealthService
from app.services.trend_service import TrendService


class ZoneNotFoundError(Exception):
    """Raised when the specified zone does not exist."""
    pass


class InconsistentSensorZoneError(Exception):
    """Raised when the sensor identifier does not match the specified zone."""
    pass


class SessionNotFoundError(Exception):
    """Raised when a specified monitoring session does not exist."""
    pass


class TelemetryService:
    """Orchestrates sensor telemetry ingestion, signal processing, and downstream health evaluation."""

    def __init__(
        self,
        db: Session,
        event_repository: Optional[EventRepository] = None,
        baseline_repository: Optional[BaselineRepository] = None,
        anomaly_service: Optional[AnomalyService] = None,
        correlation_service: Optional[CorrelationService] = None,
        trend_service: Optional[TrendService] = None,
        health_service: Optional[HealthService] = None,
    ) -> None:
        self.db = db
        self.event_repository = event_repository or EventRepository(db)
        self.baseline_repository = baseline_repository or BaselineRepository(db)
        self.anomaly_service = anomaly_service or AnomalyService(
            db,
            baseline_repository=self.baseline_repository,
            event_repository=self.event_repository,
        )
        self.correlation_service = correlation_service or CorrelationService(
            db,
            event_repository=self.event_repository,
            baseline_repository=self.baseline_repository,
            anomaly_service=self.anomaly_service,
        )
        self.trend_service = trend_service or TrendService(
            db,
            event_repository=self.event_repository,
            baseline_repository=self.baseline_repository,
            anomaly_service=self.anomaly_service,
            correlation_service=self.correlation_service,
        )
        self.health_service = health_service or HealthService(
            db,
            event_repository=self.event_repository,
            baseline_repository=self.baseline_repository,
            anomaly_service=self.anomaly_service,
            correlation_service=self.correlation_service,
            trend_service=self.trend_service,
        )

    def resolve_zone(self, zone_name: str) -> Zone:
        """Resolve a Zone by exact name, normalized name, or zone prefix."""
        normalized = zone_name.strip()
        zone = self.db.query(Zone).filter(func.lower(Zone.name) == normalized.lower()).first()
        if zone:
            return zone

        # Fallback: match by zone number if format is "Zone <N>"
        match = re.search(r"Zone\s*(\d+)", normalized, re.IGNORECASE)
        if match:
            num = match.group(1)
            zone = self.db.query(Zone).filter(Zone.name.ilike(f"%Zone {num}%")).first()
            if zone:
                return zone

        raise ZoneNotFoundError(f"Zone '{zone_name}' not found")

    def validate_sensor_zone_consistency(self, sensor_id: str, zone: Zone) -> None:
        """Verify that sensor identifier belongs to the resolved zone."""
        sensor_match = re.search(r"Z(\d+)", sensor_id, re.IGNORECASE)
        if sensor_match:
            sensor_zone_num = sensor_match.group(1)
            zone_match = re.search(r"Zone\s*(\d+)", zone.name, re.IGNORECASE)
            if zone_match:
                zone_num = zone_match.group(1)
                if sensor_zone_num != zone_num:
                    raise InconsistentSensorZoneError(
                        f"Sensor '{sensor_id}' (Zone {sensor_zone_num}) is inconsistent with target zone '{zone.name}' (Zone {zone_num})"
                    )

    def resolve_session(self, session_id: Optional[int] = None) -> MonitoringSession:
        """Resolve an active or specified MonitoringSession."""
        if session_id is not None:
            session = self.db.query(MonitoringSession).filter(MonitoringSession.id == session_id).first()
            if not session:
                raise SessionNotFoundError(f"MonitoringSession with id {session_id} not found")
            return session

        # Find latest running session
        session = (
            self.db.query(MonitoringSession)
            .filter(MonitoringSession.status == SessionStatus.RUNNING)
            .order_by(MonitoringSession.id.desc())
            .first()
        )
        if session:
            return session

        # Fallback: latest session of any status
        session = self.db.query(MonitoringSession).order_by(MonitoringSession.id.desc()).first()
        if session:
            return session

        # Create a default running session if none exists in database
        now = datetime.now(timezone.utc)
        session = MonitoringSession(
            name="Live Telemetry Monitoring Session",
            mode=SessionMode.LIVE,
            status=SessionStatus.RUNNING,
            started_at=now,
            description="Active live monitoring session for sensor telemetry ingestion.",
        )
        self.db.add(session)
        self.db.flush()
        return session

    def ingest_telemetry(self, payload: TelemetryIngestRequest) -> TelemetryIngestResponse:
        """
        Ingest discrete sensor telemetry samples and pass through the full processing pipeline.

        Flow:
        1. Resolve stable zone and validate sensor consistency.
        2. Resolve active monitoring session.
        3. Convert payload to SampledSignal.
        4. Execute signal processing pipeline (DC offset removal, filtering, event detection, feature extraction).
        5. If events detected:
           - Persist Event records.
           - Perform baseline anomaly analysis.
           - Evaluate temporal persistence and 2-PZT cross-sensor correlation.
           - Recalculate zone Structural Health Indicator (SHI).
           - Generate system Alert if structural degradation is detected.
        6. Return comprehensive structured processing result.
        """
        # 1. Resolve Zone & Sensor
        zone = self.resolve_zone(payload.zone_name)
        self.validate_sensor_zone_consistency(payload.sensor_id, zone)

        # 2. Resolve Monitoring Session
        session = self.resolve_session(payload.session_id)

        # 3. Construct SampledSignal
        signal = SampledSignal(
            samples=np.asarray(payload.samples, dtype=np.float64),
            sample_rate_hz=float(payload.sample_rate_hz),
            timestamp=payload.timestamp,
            source_id=payload.sensor_id,
        )

        # 4. Determine event detection threshold
        baseline = self.baseline_repository.get_latest_for_zone(zone.id)
        if payload.detection_threshold is not None:
            threshold = float(payload.detection_threshold)
        elif baseline and baseline.mean_magnitude is not None and baseline.std_magnitude is not None:
            # Baseline-informed detection threshold (mean + 2*sigma)
            threshold = max(0.1, float(baseline.mean_magnitude + 2.0 * baseline.std_magnitude))
        else:
            threshold = 1.0

        # 5. Execute Signal Processing Pipeline
        processed_events: List[ProcessedEvent] = process_signal_pipeline(
            signal=signal,
            detection_threshold=threshold,
            remove_dc=True,
            filter_window_size=3 if len(signal.samples) >= 5 else None,
            min_duration_samples=1,
            merge_gap_samples=2,
        )

        sample_count = len(payload.samples)

        # Case A: No events detected (quiet / below-threshold signal)
        if len(processed_events) == 0:
            return TelemetryIngestResponse(
                status="PROCESSED_NO_EVENT",
                telemetry_accepted=True,
                sensor_id=payload.sensor_id,
                zone_id=zone.id,
                zone_name=zone.name,
                timestamp=payload.timestamp,
                samples_count=sample_count,
                sample_rate_hz=payload.sample_rate_hz,
                sequence=payload.sequence,
                events_detected=0,
                events=[],
                extracted_features=None,
                temporal_persistence_confirmed=False,
                cross_sensor_correlation_confirmed=False,
                health_score=None,
                health_status=None,
                health_trend=None,
                alert_generated=False,
                alert_id=None,
                alert_severity=None,
                alert_title=None,
                message=f"Telemetry from '{payload.sensor_id}' processed. Signal activity remained below detection threshold ({threshold:.2f}).",
            )

        # Case B: Events detected -> execute downstream pipeline
        event_results: List[TelemetryEventResult] = []
        first_features: Optional[ExtractedFeaturesSchema] = None
        has_any_anomaly = False

        for p_event in processed_events:
            # Set extracted features schema from first detected event window
            if first_features is None:
                first_features = ExtractedFeaturesSchema(
                    peak_amplitude=p_event.magnitude,
                    rms_amplitude=p_event.rms_amplitude,
                    energy=p_event.energy,
                    duration_ms=p_event.duration_ms,
                    frequency_hz=p_event.frequency_hz,
                    sample_count=p_event.sample_count,
                )

            # Determine initial severity rating against baseline z-score
            sev = EventSeverity.LOW
            if baseline and baseline.mean_magnitude is not None and baseline.std_magnitude is not None:
                std_m = baseline.std_magnitude if baseline.std_magnitude > 0 else 1.0
                std_e = baseline.std_energy if baseline.std_energy > 0 else 1.0
                z_mag = abs((p_event.magnitude - baseline.mean_magnitude) / std_m)
                z_eng = abs((p_event.energy - baseline.mean_energy) / std_e)
                max_z = max(z_mag, z_eng)
                if max_z >= 4.0:
                    sev = EventSeverity.CRITICAL
                elif max_z >= 3.0:
                    sev = EventSeverity.HIGH
                elif max_z >= 2.0:
                    sev = EventSeverity.MEDIUM

            # Persist Event to database
            db_event = Event(
                session_id=session.id,
                zone_id=zone.id,
                source_type=EventSourceType.SENSOR,
                source_id=payload.sensor_id,
                correlation_id=None,
                timestamp=p_event.timestamp,
                magnitude=p_event.magnitude,
                energy=p_event.energy,
                duration_ms=p_event.duration_ms,
                frequency_hz=p_event.frequency_hz,
                severity=sev,
                status=EventStatus.DETECTED,
                metadata_json={
                    "sequence": payload.sequence,
                    "sample_rate_hz": payload.sample_rate_hz,
                    "sample_count": p_event.sample_count,
                    "rms_amplitude": p_event.rms_amplitude,
                    "detection_threshold": threshold,
                    **p_event.features,
                },
            )
            self.db.add(db_event)
            self.db.flush()

            # Statistical anomaly evaluation
            is_anom = False
            z_mag_val: Optional[float] = None
            z_eng_val: Optional[float] = None
            reasons: List[str] = []

            if baseline:
                try:
                    anom_res = self.anomaly_service.analyze_event_by_id(db_event.id)
                    is_anom = anom_res.is_anomalous
                    z_mag_val = anom_res.magnitude_z_score
                    z_eng_val = anom_res.energy_z_score
                    reasons = list(anom_res.reasons)
                except (BaselineNotFoundError, InvalidEventDataError):
                    pass

            if is_anom:
                has_any_anomaly = True

            event_results.append(
                TelemetryEventResult(
                    event_id=db_event.id,
                    magnitude=p_event.magnitude,
                    energy=p_event.energy,
                    duration_ms=p_event.duration_ms,
                    frequency_hz=p_event.frequency_hz,
                    severity=sev,
                    is_anomalous=is_anom,
                    magnitude_z_score=z_mag_val,
                    energy_z_score=z_eng_val,
                    anomaly_reasons=reasons,
                )
            )

        # Temporal persistence & 2-PZT cross-sensor correlation
        ref_time = processed_events[0].timestamp
        persistence_res = self.correlation_service.evaluate_zone_persistence(
            zone_id=zone.id,
            reference_time=ref_time,
            window_duration_seconds=300.0,
        )
        corr_groups = self.correlation_service.correlate_zone_events(
            zone_id=zone.id,
            valid_from=ref_time - timedelta(seconds=300),
            valid_until=ref_time,
        )
        is_cross_sensor = any(g.is_cross_sensor for g in corr_groups)

        # Health (SHI) evaluation & snapshot persistence
        health_res = self.health_service.evaluate_zone_health(
            zone_id=zone.id,
            session_id=session.id,
            reference_time=ref_time,
            window_duration_seconds=3600.0,
            persist_snapshot=True,
        )

        # Alert generation check
        alert_generated = False
        alert_id: Optional[int] = None
        alert_sev: Optional[AlertSeverity] = None
        alert_title: Optional[str] = None

        if health_res.status in (HealthStatus.INSPECTION_ADVISED, HealthStatus.HIGH_PRIORITY_INSPECTION):
            snapshot = (
                self.db.query(HealthSnapshot)
                .filter(HealthSnapshot.zone_id == zone.id)
                .order_by(HealthSnapshot.timestamp.desc(), HealthSnapshot.id.desc())
                .first()
            )
            if snapshot:
                alert_sev = (
                    AlertSeverity.HIGH
                    if health_res.status == HealthStatus.HIGH_PRIORITY_INSPECTION
                    else AlertSeverity.MEDIUM
                )
                alert_title = f"Structural Health Anomaly in {zone.name}"
                alert = Alert(
                    health_snapshot_id=snapshot.id,
                    zone_id=zone.id,
                    timestamp=ref_time,
                    severity=alert_sev,
                    title=alert_title,
                    message=health_res.reason,
                    status=AlertStatus.ACTIVE,
                )
                self.db.add(alert)
                self.db.flush()
                alert_generated = True
                alert_id = alert.id

        # Commit all changes atomically
        self.db.commit()

        status_str = "PROCESSED_ANOMALY_DETECTED" if has_any_anomaly else "PROCESSED_EVENT_DETECTED"
        msg = (
            f"Telemetry from '{payload.sensor_id}' processed: {len(processed_events)} event(s) detected. "
            f"SHI: {health_res.score:.1f}/100 ({health_res.status.value})."
        )
        if alert_generated:
            msg += f" Active alert #{alert_id} ({alert_sev.value}) generated."

        return TelemetryIngestResponse(
            status=status_str,
            telemetry_accepted=True,
            sensor_id=payload.sensor_id,
            zone_id=zone.id,
            zone_name=zone.name,
            timestamp=payload.timestamp,
            samples_count=sample_count,
            sample_rate_hz=payload.sample_rate_hz,
            sequence=payload.sequence,
            events_detected=len(processed_events),
            events=event_results,
            extracted_features=first_features,
            temporal_persistence_confirmed=persistence_res.is_persistent,
            cross_sensor_correlation_confirmed=is_cross_sensor,
            health_score=health_res.score,
            health_status=health_res.status,
            health_trend=health_res.trend,
            alert_generated=alert_generated,
            alert_id=alert_id,
            alert_severity=alert_sev,
            alert_title=alert_title,
            message=msg,
        )
