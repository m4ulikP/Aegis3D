"""Service layer orchestrating raw sensor telemetry ingestion and signal processing pipeline."""

from datetime import datetime, timedelta, timezone
import re
from typing import Dict, List, Optional
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
    DetectedWindow,
    ProcessedEvent,
    SampledSignal,
    detect_events,
    extract_features,
    moving_average_filter,
    process_signal_pipeline,
    remove_dc_offset,
)
from app.repositories.baseline_repository import BaselineRepository
from app.repositories.event_repository import EventRepository
from app.schemas.processing_trace import (
    AlertTrace,
    AnomalyEvaluationTrace,
    BaselineTrace,
    ConditioningTrace,
    CorrelationTrace,
    DetectedWindowTrace,
    EventDetectionTrace,
    FeatureExtractionTrace,
    HealthTrace,
    PersistenceTrace,
    ProcessingTraceResponse,
    RawTelemetryTrace,
    TraceMetadata,
    TrendTrace,
)
from app.schemas.telemetry import (
    ExtractedFeaturesSchema,
    TelemetryEventResult,
    TelemetryIngestRequest,
    TelemetryIngestResponse,
    TelemetryLatestResponse,
)
from app.schemas.live_telemetry import (
    LiveEventType,
    LiveProcessingEvent,
    ProcessingStage,
    stage_to_index,
)
from app.services.anomaly_service import AnomalyService
from app.services.correlation_service import CorrelationService
from app.services.health_service import HealthService
from app.services.live_bus import get_live_event_bus
from app.services.trend_service import TrendService


# Thread-safe in-memory cache of latest ingested telemetry snapshots keyed by stable sensor_id
_latest_telemetry_by_sensor: Dict[str, TelemetryLatestResponse] = {}
_most_recent_sensor_id: Optional[str] = None

# Thread-safe in-memory cache of processing traces keyed by trace_id, event_id, sensor_id, and 'latest'
_processing_traces: Dict[str, ProcessingTraceResponse] = {}
_most_recent_trace_id: Optional[str] = None


def _get_latest_snapshot(sensor_id: Optional[str] = None) -> Optional[TelemetryLatestResponse]:
    """Retrieve the latest telemetry snapshot for a specific sensor or the most recently received sensor."""
    if sensor_id is not None:
        return _latest_telemetry_by_sensor.get(sensor_id.strip())
    if _most_recent_sensor_id and _most_recent_sensor_id in _latest_telemetry_by_sensor:
        return _latest_telemetry_by_sensor[_most_recent_sensor_id]
    return None


def _set_latest_snapshot(snapshot: TelemetryLatestResponse) -> None:
    """Store latest telemetry snapshot keyed by stable sensor_id and mark as most recent."""
    global _most_recent_sensor_id
    if snapshot and snapshot.sensor_id:
        sid = snapshot.sensor_id.strip()
        _latest_telemetry_by_sensor[sid] = snapshot
        _most_recent_sensor_id = sid


def _get_cached_processing_trace(identifier: str) -> Optional[ProcessingTraceResponse]:
    """Retrieve cached processing trace by identifier."""
    key = identifier.strip()
    if key in _processing_traces:
        return _processing_traces[key]
    if key == "latest" and _most_recent_trace_id and _most_recent_trace_id in _processing_traces:
        return _processing_traces[_most_recent_trace_id]
    return None


def _set_processing_trace(trace: ProcessingTraceResponse) -> None:
    """Store processing trace in memory and update lookup keys."""
    global _most_recent_trace_id
    tid = trace.metadata.trace_id
    _processing_traces[tid] = trace
    _processing_traces[trace.metadata.sensor_id] = trace
    _processing_traces["latest"] = trace
    if trace.metadata.event_id is not None:
        _processing_traces[str(trace.metadata.event_id)] = trace
    _most_recent_trace_id = tid


def _set_processing_trace_alias(key: str, trace: ProcessingTraceResponse) -> None:
    """Map an additional key (e.g. secondary event_id) to a trace."""
    _processing_traces[key.strip()] = trace


def _emit_pipeline_event(
    event_type: LiveEventType,
    stage: Optional[ProcessingStage] = None,
    status: str = "started",
    trace_id: Optional[str] = None,
    event_id: Optional[int] = None,
    sensor_id: Optional[str] = None,
    zone_id: Optional[int] = None,
    zone_name: Optional[str] = None,
    sequence: Optional[int] = None,
    summary: Optional[str] = None,
    error_message: Optional[str] = None,
    duration_ms: Optional[float] = None,
) -> None:
    """Safely publish an event to the in-process live event bus without interrupting ingestion."""
    try:
        bus = get_live_event_bus()
        event = LiveProcessingEvent(
            type=event_type,
            stage=stage,
            stage_index=stage_to_index(stage) if stage else None,
            status=status,
            trace_id=trace_id,
            event_id=event_id,
            sensor_id=sensor_id,
            zone_id=zone_id,
            zone_name=zone_name,
            sequence=sequence,
            summary=summary,
            error_message=error_message,
            duration_ms=duration_ms,
            timestamp=datetime.now(timezone.utc),
        )
        bus.publish(event)
    except Exception:
        # Event bus emission must never break ingestion
        pass


def _clear_all_telemetry_caches() -> None:
    """Clear all cached sensor snapshots and processing traces (for testing purposes)."""
    global _most_recent_sensor_id, _most_recent_trace_id
    _latest_telemetry_by_sensor.clear()
    _most_recent_sensor_id = None
    _processing_traces.clear()
    _most_recent_trace_id = None


def _create_bounded_display_samples(samples: List[float], max_points: int = 500) -> List[float]:
    """Window or downsample raw discrete values to a bounded array for HUD visualization."""
    if len(samples) <= max_points:
        return [float(s) for s in samples]
    step = len(samples) / float(max_points)
    return [float(samples[int(i * step)]) for i in range(max_points)]


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

    @classmethod
    def get_latest_telemetry(cls, sensor_id: Optional[str] = None) -> Optional[TelemetryLatestResponse]:
        """Retrieve the latest ingested telemetry record for a specific sensor or the most recently received sensor."""
        return _get_latest_snapshot(sensor_id=sensor_id)

    @classmethod
    def clear_latest_telemetry(cls) -> None:
        """Clear cached telemetry snapshots and traces (useful for testing)."""
        _clear_all_telemetry_caches()

    @classmethod
    def clear_processing_traces(cls) -> None:
        """Clear cached processing traces (useful for testing)."""
        _clear_all_telemetry_caches()

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

    # Canonical sensor → zone lookup.
    # PZT-Z01…Z06 → Zone 1 (Main Deck Girder)
    # PZT-Z07…Z12 → Zone 2 (Substructure Pier B)
    _CANONICAL_SENSOR_ZONE_MAP: Dict[int, int] = {
        **{n: 1 for n in range(1, 7)},
        **{n: 2 for n in range(7, 13)},
    }

    def validate_sensor_zone_consistency(self, sensor_id: str, zone: Zone) -> None:
        """Verify that sensor identifier belongs to the resolved zone.

        Two-path validation:
        - Canonical format ``PZT-ZNN`` (e.g. PZT-Z01…PZT-Z12): checked via the
          built-in _CANONICAL_SENSOR_ZONE_MAP so that PZT-Z07 correctly maps to
          Zone 2 even though its numeric suffix (7) does not match "Zone 2".
        - Legacy format ``PZT-Z<zone>-<node>`` (e.g. PZT-Z1-01): falls back to
          the original regex-based zone number comparison.
        """
        # ── Canonical format: exactly PZT-Z followed by two digits ──────────
        canonical_match = re.fullmatch(
            r"PZT-Z(\d{2})", sensor_id, re.IGNORECASE
        )
        if canonical_match:
            sensor_num = int(canonical_match.group(1))
            expected_zone_num = self._CANONICAL_SENSOR_ZONE_MAP.get(sensor_num)
            if expected_zone_num is not None:
                zone_match = re.search(r"Zone\s*(\d+)", zone.name, re.IGNORECASE)
                if zone_match:
                    zone_num = int(zone_match.group(1))
                    if expected_zone_num != zone_num:
                        raise InconsistentSensorZoneError(
                            f"Sensor '{sensor_id}' (canonical Zone {expected_zone_num}) "
                            f"was submitted to '{zone.name}' (Zone {zone_num})"
                        )
            # Canonical sensor accepted even if zone number is not DB-registered
            return

        # ── Legacy format: PZT-Z<zone>-<node> or any other pattern ─────────
        sensor_match = re.search(r"Z(\d+)", sensor_id, re.IGNORECASE)
        if sensor_match:
            sensor_zone_num = int(sensor_match.group(1))
            zone_match = re.search(r"Zone\s*(\d+)", zone.name, re.IGNORECASE)
            if zone_match:
                zone_num = int(zone_match.group(1))
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
        6. Construct detailed processing trace and return structured processing result.
        """
        prelim_trace_id = f"trace-{payload.sensor_id}-{payload.sequence if payload.sequence is not None else int(payload.timestamp.timestamp())}"
        current_trace_id = prelim_trace_id
        active_stage = ProcessingStage.INGESTION

        try:
            # 0. Pipeline Started
            _emit_pipeline_event(
                LiveEventType.PROCESSING_STARTED,
                trace_id=current_trace_id,
                sensor_id=payload.sensor_id,
                sequence=payload.sequence,
                summary=f"Telemetry packet accepted from '{payload.sensor_id}'",
            )

            # 1. INGESTION Stage Started
            _emit_pipeline_event(
                LiveEventType.STAGE_STARTED,
                stage=ProcessingStage.INGESTION,
                status="started",
                trace_id=current_trace_id,
                sensor_id=payload.sensor_id,
                sequence=payload.sequence,
                summary="Ingesting discrete sensor samples and validating zone consistency",
            )

            # 1. Resolve Zone & Sensor
            zone = self.resolve_zone(payload.zone_name)
            self.validate_sensor_zone_consistency(payload.sensor_id, zone)

            # 2. Resolve Monitoring Session
            session = self.resolve_session(payload.session_id)

            # 3. Construct SampledSignal
            raw_samples_arr = np.asarray(payload.samples, dtype=np.float64)
            signal = SampledSignal(
                samples=raw_samples_arr,
                sample_rate_hz=float(payload.sample_rate_hz),
                timestamp=payload.timestamp,
                source_id=payload.sensor_id,
            )

            sample_count = len(payload.samples)
            raw_mean_dc = float(np.mean(raw_samples_arr)) if sample_count > 0 else 0.0
            raw_peak = float(np.max(np.abs(raw_samples_arr))) if sample_count > 0 else 0.0
            raw_rms = float(np.sqrt(np.mean(np.square(raw_samples_arr)))) if sample_count > 0 else 0.0

            # 1. INGESTION Stage Completed
            _emit_pipeline_event(
                LiveEventType.STAGE_COMPLETED,
                stage=ProcessingStage.INGESTION,
                status="completed",
                trace_id=current_trace_id,
                sensor_id=payload.sensor_id,
                zone_id=zone.id,
                zone_name=zone.name,
                sequence=payload.sequence,
                summary=f"{sample_count} pts @ {payload.sample_rate_hz}Hz (peak: {raw_peak:.2f} mm/s²)",
            )

            # 2. CONDITIONING Stage Started
            active_stage = ProcessingStage.CONDITIONING
            _emit_pipeline_event(
                LiveEventType.STAGE_STARTED,
                stage=ProcessingStage.CONDITIONING,
                status="started",
                trace_id=current_trace_id,
                sensor_id=payload.sensor_id,
                zone_id=zone.id,
                zone_name=zone.name,
                sequence=payload.sequence,
                summary="Applying DC offset removal and moving-average filter",
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

            # 5. Execute Signal Processing Pipeline (Conditioning -> Event Detection -> Feature Extraction)
            filter_win = 3 if sample_count >= 5 else None
            proc_signal = remove_dc_offset(signal)
            if filter_win is not None:
                proc_signal = moving_average_filter(proc_signal, window_size=filter_win)

            # 2. CONDITIONING Stage Completed
            _emit_pipeline_event(
                LiveEventType.STAGE_COMPLETED,
                stage=ProcessingStage.CONDITIONING,
                status="completed",
                trace_id=current_trace_id,
                sensor_id=payload.sensor_id,
                zone_id=zone.id,
                zone_name=zone.name,
                sequence=payload.sequence,
                summary=f"DC offset removed ({raw_mean_dc:+.2f}), filter window: {filter_win or 1}",
            )

            # 3. EVENT DETECTION Stage Started
            active_stage = ProcessingStage.EVENT_DETECTION
            _emit_pipeline_event(
                LiveEventType.STAGE_STARTED,
                stage=ProcessingStage.EVENT_DETECTION,
                status="started",
                trace_id=current_trace_id,
                sensor_id=payload.sensor_id,
                zone_id=zone.id,
                zone_name=zone.name,
                sequence=payload.sequence,
                summary=f"Detecting energy bursts against threshold {threshold:.2f}",
            )

            windows: List[DetectedWindow] = detect_events(
                proc_signal,
                threshold=threshold,
                min_duration_samples=1,
                merge_gap_samples=2,
            )

            processed_events: List[ProcessedEvent] = []
            for win in windows:
                p_event = extract_features(proc_signal, win)
                processed_events.append(p_event)

            bounded_raw_samples = _create_bounded_display_samples(payload.samples)
            bounded_cond_samples = _create_bounded_display_samples(proc_signal.samples.tolist())

            # Build baseline trace representation
            baseline_trace = BaselineTrace(
                baseline_id=baseline.id if baseline else None,
                zone_id=zone.id,
                mean_magnitude=baseline.mean_magnitude if baseline else None,
                std_magnitude=baseline.std_magnitude if baseline else None,
                mean_energy=baseline.mean_energy if baseline else None,
                std_energy=baseline.std_energy if baseline else None,
                normal_event_rate=baseline.normal_event_rate if baseline else None,
                valid_from=baseline.valid_from if baseline else None,
                valid_until=baseline.valid_until if baseline else None,
                baseline_available=baseline is not None,
            )

            # 3. EVENT DETECTION Stage Completed
            _emit_pipeline_event(
                LiveEventType.STAGE_COMPLETED,
                stage=ProcessingStage.EVENT_DETECTION,
                status="completed",
                trace_id=current_trace_id,
                sensor_id=payload.sensor_id,
                zone_id=zone.id,
                zone_name=zone.name,
                sequence=payload.sequence,
                summary=f"{len(windows)} event window(s) detected (threshold: {threshold:.2f})"
                if len(windows) > 0
                else f"Below threshold ({threshold:.2f})",
            )

            # Case A: No events detected (quiet / below-threshold signal)
            if len(processed_events) == 0:
                for st, summary_txt in [
                    (ProcessingStage.FEATURE_EXTRACTION, "Sub-threshold signal; feature extraction bypassed"),
                    (ProcessingStage.BASELINE_REFERENCE, f"Zone baseline id={baseline.id} active" if baseline else "No baseline established"),
                    (ProcessingStage.ANOMALY_EVALUATION, "Quiet baseline envelope; anomaly evaluation not triggered"),
                    (ProcessingStage.PERSISTENCE, "No events detected in current telemetry packet"),
                    (ProcessingStage.CROSS_SENSOR_CORRELATION, "No events detected in current telemetry packet"),
                    (ProcessingStage.HEALTH_AND_ALERT, "Signal within quiet baseline envelope"),
                ]:
                    active_stage = st
                    _emit_pipeline_event(
                        LiveEventType.STAGE_STARTED,
                        stage=st,
                        status="started",
                        trace_id=current_trace_id,
                        sensor_id=payload.sensor_id,
                        zone_id=zone.id,
                        zone_name=zone.name,
                        sequence=payload.sequence,
                    )
                    _emit_pipeline_event(
                        LiveEventType.STAGE_COMPLETED,
                        stage=st,
                        status="completed",
                        trace_id=current_trace_id,
                        sensor_id=payload.sensor_id,
                        zone_id=zone.id,
                        zone_name=zone.name,
                        sequence=payload.sequence,
                        summary=summary_txt,
                    )

                res = TelemetryIngestResponse(
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
                _set_latest_snapshot(
                    TelemetryLatestResponse(
                        **res.model_dump(),
                        samples=bounded_raw_samples,
                        detection_threshold=threshold,
                    )
                )

                # Record processing trace for quiet packet
                trace_id = f"trace-{payload.sensor_id}-{payload.sequence if payload.sequence is not None else int(payload.timestamp.timestamp())}"
                trace_resp = ProcessingTraceResponse(
                    metadata=TraceMetadata(
                        trace_id=trace_id,
                        event_id=None,
                        sensor_id=payload.sensor_id,
                        zone_id=zone.id,
                        zone_name=zone.name,
                        timestamp=payload.timestamp,
                        sequence=payload.sequence,
                        sample_rate_hz=payload.sample_rate_hz,
                        samples_count=sample_count,
                        session_id=session.id,
                    ),
                    ingestion=RawTelemetryTrace(
                        sensor_id=payload.sensor_id,
                        zone_name=zone.name,
                        timestamp=payload.timestamp,
                        sample_rate_hz=payload.sample_rate_hz,
                        samples_count=sample_count,
                        sequence=payload.sequence,
                        samples_bounded=bounded_raw_samples,
                        peak_amplitude=raw_peak,
                        rms_amplitude=raw_rms,
                        is_bounded=sample_count > 500,
                    ),
                    conditioning=ConditioningTrace(
                        dc_removal_applied=True,
                        dc_offset_removed=raw_mean_dc,
                        filter_applied=filter_win is not None,
                        filter_type="MOVING_AVERAGE" if filter_win is not None else None,
                        filter_window_size=filter_win,
                        conditioned_samples_bounded=bounded_cond_samples,
                    ),
                    event_detection=EventDetectionTrace(
                        detection_threshold=threshold,
                        events_detected_count=0,
                        events_detected=False,
                        min_duration_samples=1,
                        merge_gap_samples=2,
                        detected_windows=[],
                    ),
                    features=None,
                    baseline=baseline_trace,
                    anomaly=AnomalyEvaluationTrace(
                        evaluated=False,
                        is_anomalous=False,
                        z_threshold=3.0,
                        reasons=["Signal activity below detection threshold; anomaly evaluation not triggered."],
                    ),
                    persistence=PersistenceTrace(
                        evaluated=False,
                        is_persistent=False,
                        reasons=["No structural events detected in current telemetry packet."],
                    ),
                    correlation=CorrelationTrace(
                        evaluated=False,
                        is_cross_sensor_correlated=False,
                        reasons=["No structural events detected in current telemetry packet."],
                    ),
                    trend=TrendTrace(
                        evaluated=False,
                        overall_trend=None,
                        reasons=["No structural events detected in current telemetry packet."],
                    ),
                    health=HealthTrace(
                        evaluated=False,
                        health_score=None,
                        health_status=None,
                        evidence_summary=["Signal activity within quiet baseline envelope."],
                    ),
                    alert=AlertTrace(
                        alert_generated=False,
                    ),
                )
                _set_processing_trace(trace_resp)

                # 10. PROCESSING COMPLETED (quiet packet)
                _emit_pipeline_event(
                    LiveEventType.PROCESSING_COMPLETED,
                    status="completed",
                    trace_id=trace_id,
                    sensor_id=payload.sensor_id,
                    zone_id=zone.id,
                    zone_name=zone.name,
                    sequence=payload.sequence,
                    summary=f"Processed quiet telemetry packet from {payload.sensor_id}",
                )

                return res

            # Case B: Events detected -> execute downstream pipeline
            # 4. FEATURE EXTRACTION Stage Started
            active_stage = ProcessingStage.FEATURE_EXTRACTION
            _emit_pipeline_event(
                LiveEventType.STAGE_STARTED,
                stage=ProcessingStage.FEATURE_EXTRACTION,
                status="started",
                trace_id=current_trace_id,
                sensor_id=payload.sensor_id,
                zone_id=zone.id,
                zone_name=zone.name,
                sequence=payload.sequence,
                summary=f"Extracting features for {len(processed_events)} detected window(s)",
            )

            event_results: List[TelemetryEventResult] = []
            first_features: Optional[ExtractedFeaturesSchema] = None
            has_any_anomaly = False
            primary_anomaly_res = None

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
                        if primary_anomaly_res is None:
                            primary_anomaly_res = anom_res
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

            # 4. FEATURE EXTRACTION Stage Completed
            _emit_pipeline_event(
                LiveEventType.STAGE_COMPLETED,
                stage=ProcessingStage.FEATURE_EXTRACTION,
                status="completed",
                trace_id=current_trace_id,
                sensor_id=payload.sensor_id,
                zone_id=zone.id,
                zone_name=zone.name,
                sequence=payload.sequence,
                summary=f"Peak: {first_features.peak_amplitude:.2f} mm/s², Energy: {first_features.energy:.2f}, Freq: {first_features.frequency_hz or 0.0:.1f}Hz"
                if first_features
                else "Features extracted",
            )

            # 5. BASELINE REFERENCE Stage Started & Completed
            active_stage = ProcessingStage.BASELINE_REFERENCE
            _emit_pipeline_event(
                LiveEventType.STAGE_STARTED,
                stage=ProcessingStage.BASELINE_REFERENCE,
                status="started",
                trace_id=current_trace_id,
                sensor_id=payload.sensor_id,
                zone_id=zone.id,
                zone_name=zone.name,
                sequence=payload.sequence,
                summary=f"Referencing zone baseline norms for zone {zone.name}",
            )
            _emit_pipeline_event(
                LiveEventType.STAGE_COMPLETED,
                stage=ProcessingStage.BASELINE_REFERENCE,
                status="completed",
                trace_id=current_trace_id,
                sensor_id=payload.sensor_id,
                zone_id=zone.id,
                zone_name=zone.name,
                sequence=payload.sequence,
                summary=f"Baseline mean={baseline.mean_magnitude:.2f}, std={baseline.std_magnitude:.2f}"
                if baseline
                else "No baseline established for zone",
            )

            # 6. ANOMALY EVALUATION Stage Started & Completed
            active_stage = ProcessingStage.ANOMALY_EVALUATION
            primary_db_event_id = event_results[0].event_id if event_results else None
            if primary_db_event_id:
                current_trace_id = f"trace-evt-{primary_db_event_id}"

            primary_res = event_results[0]
            _emit_pipeline_event(
                LiveEventType.STAGE_STARTED,
                stage=ProcessingStage.ANOMALY_EVALUATION,
                status="started",
                trace_id=current_trace_id,
                event_id=primary_db_event_id,
                sensor_id=payload.sensor_id,
                zone_id=zone.id,
                zone_name=zone.name,
                sequence=payload.sequence,
                summary="Computing standardized z-scores against baseline distribution",
            )
            anom_summary = (
                f"Z-mag: {primary_res.magnitude_z_score:+.2f}σ, Z-energy: {primary_res.energy_z_score:+.2f}σ — {'ANOMALOUS' if primary_res.is_anomalous else 'NORMAL'}"
                if primary_res.magnitude_z_score is not None
                else "Evaluated against zone baseline"
            )
            _emit_pipeline_event(
                LiveEventType.STAGE_COMPLETED,
                stage=ProcessingStage.ANOMALY_EVALUATION,
                status="completed",
                trace_id=current_trace_id,
                event_id=primary_db_event_id,
                sensor_id=payload.sensor_id,
                zone_id=zone.id,
                zone_name=zone.name,
                sequence=payload.sequence,
                summary=anom_summary,
            )

            # 7. PERSISTENCE Stage Started
            active_stage = ProcessingStage.PERSISTENCE
            _emit_pipeline_event(
                LiveEventType.STAGE_STARTED,
                stage=ProcessingStage.PERSISTENCE,
                status="started",
                trace_id=current_trace_id,
                event_id=primary_db_event_id,
                sensor_id=payload.sensor_id,
                zone_id=zone.id,
                zone_name=zone.name,
                sequence=payload.sequence,
                summary="Evaluating rolling temporal anomaly persistence over 300s window",
            )

            # Temporal persistence & 2-PZT cross-sensor correlation
            ref_time = processed_events[0].timestamp
            persistence_res = self.correlation_service.evaluate_zone_persistence(
                zone_id=zone.id,
                reference_time=ref_time,
                window_duration_seconds=300.0,
            )

            # 7. PERSISTENCE Stage Completed
            _emit_pipeline_event(
                LiveEventType.STAGE_COMPLETED,
                stage=ProcessingStage.PERSISTENCE,
                status="completed",
                trace_id=current_trace_id,
                event_id=primary_db_event_id,
                sensor_id=payload.sensor_id,
                zone_id=zone.id,
                zone_name=zone.name,
                sequence=payload.sequence,
                summary=f"Persistence {'CONFIRMED' if persistence_res.is_persistent else 'NEGATIVE'} ({persistence_res.anomalous_events}/{persistence_res.total_events} anomalies in 300s)",
            )

            # 8. CROSS-SENSOR CORRELATION Stage Started
            active_stage = ProcessingStage.CROSS_SENSOR_CORRELATION
            _emit_pipeline_event(
                LiveEventType.STAGE_STARTED,
                stage=ProcessingStage.CROSS_SENSOR_CORRELATION,
                status="started",
                trace_id=current_trace_id,
                event_id=primary_db_event_id,
                sensor_id=payload.sensor_id,
                zone_id=zone.id,
                zone_name=zone.name,
                sequence=payload.sequence,
                summary="Evaluating 2-PZT arrival time spread and relative source indication",
            )

            corr_groups = self.correlation_service.correlate_zone_events(
                zone_id=zone.id,
                valid_from=ref_time - timedelta(seconds=300),
                valid_until=ref_time,
            )
            is_cross_sensor = any(g.is_cross_sensor for g in corr_groups)

            primary_group = next((g for g in corr_groups if primary_res.event_id in g.event_ids), None)
            if primary_group is None and corr_groups:
                primary_group = corr_groups[0]

            corr_summary = (
                primary_group.relative_source_hint
                if (primary_group and primary_group.relative_source_hint)
                else ("Multi-sensor cross-sensor correlation confirmed" if is_cross_sensor else "Single sensor localized excitation")
            )

            # 8. CROSS-SENSOR CORRELATION Stage Completed
            _emit_pipeline_event(
                LiveEventType.STAGE_COMPLETED,
                stage=ProcessingStage.CROSS_SENSOR_CORRELATION,
                status="completed",
                trace_id=current_trace_id,
                event_id=primary_db_event_id,
                sensor_id=payload.sensor_id,
                zone_id=zone.id,
                zone_name=zone.name,
                sequence=payload.sequence,
                summary=corr_summary,
            )

            # 9. HEALTH & ALERT Stage Started
            active_stage = ProcessingStage.HEALTH_AND_ALERT
            _emit_pipeline_event(
                LiveEventType.STAGE_STARTED,
                stage=ProcessingStage.HEALTH_AND_ALERT,
                status="started",
                trace_id=current_trace_id,
                event_id=primary_db_event_id,
                sensor_id=payload.sensor_id,
                zone_id=zone.id,
                zone_name=zone.name,
                sequence=payload.sequence,
                summary="Computing Structural Health Index (SHI 0–100) and alert dispatch",
            )

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

            # 9. HEALTH & ALERT Stage Completed
            _emit_pipeline_event(
                LiveEventType.STAGE_COMPLETED,
                stage=ProcessingStage.HEALTH_AND_ALERT,
                status="completed",
                trace_id=current_trace_id,
                event_id=primary_db_event_id,
                sensor_id=payload.sensor_id,
                zone_id=zone.id,
                zone_name=zone.name,
                sequence=payload.sequence,
                summary=f"SHI: {health_res.score:.1f}/100 ({health_res.status.value}), Alert: {alert_generated}",
            )

            status_str = "PROCESSED_ANOMALY_DETECTED" if has_any_anomaly else "PROCESSED_EVENT_DETECTED"
            msg = (
                f"Telemetry from '{payload.sensor_id}' processed: {len(processed_events)} event(s) detected. "
                f"SHI: {health_res.score:.1f}/100 ({health_res.status.value})."
            )
            if alert_generated:
                msg += f" Active alert #{alert_id} ({alert_sev.value}) generated."

            res = TelemetryIngestResponse(
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
            _set_latest_snapshot(
                TelemetryLatestResponse(
                    **res.model_dump(),
                    samples=bounded_raw_samples,
                    detection_threshold=threshold,
                )
            )

            # Build comprehensive processing trace for detected event run
            first_p_evt = processed_events[0]
            trace_id = f"trace-evt-{primary_res.event_id}"
            trace_resp = ProcessingTraceResponse(
                metadata=TraceMetadata(
                    trace_id=trace_id,
                    event_id=primary_res.event_id,
                    sensor_id=payload.sensor_id,
                    zone_id=zone.id,
                    zone_name=zone.name,
                    timestamp=payload.timestamp,
                    sequence=payload.sequence,
                    sample_rate_hz=payload.sample_rate_hz,
                    samples_count=sample_count,
                    session_id=session.id,
                ),
                ingestion=RawTelemetryTrace(
                    sensor_id=payload.sensor_id,
                    zone_name=zone.name,
                    timestamp=payload.timestamp,
                    sample_rate_hz=payload.sample_rate_hz,
                    samples_count=sample_count,
                    sequence=payload.sequence,
                    samples_bounded=bounded_raw_samples,
                    peak_amplitude=raw_peak,
                    rms_amplitude=raw_rms,
                    is_bounded=sample_count > 500,
                ),
                conditioning=ConditioningTrace(
                    dc_removal_applied=True,
                    dc_offset_removed=raw_mean_dc,
                    filter_applied=filter_win is not None,
                    filter_type="MOVING_AVERAGE" if filter_win is not None else None,
                    filter_window_size=filter_win,
                    conditioned_samples_bounded=bounded_cond_samples,
                ),
                event_detection=EventDetectionTrace(
                    detection_threshold=threshold,
                    events_detected_count=len(processed_events),
                    events_detected=True,
                    min_duration_samples=1,
                    merge_gap_samples=2,
                    detected_windows=[
                        DetectedWindowTrace(
                            start_index=w.start_index,
                            end_index=w.end_index,
                            start_time_ms=w.start_time_ms,
                            end_time_ms=w.end_time_ms,
                            duration_ms=w.duration_ms,
                            peak_amplitude=w.peak_amplitude,
                            rms_amplitude=w.rms_amplitude,
                            sample_count=w.sample_count,
                        )
                        for w in windows
                    ],
                ),
                features=FeatureExtractionTrace(
                    event_id=primary_res.event_id,
                    peak_amplitude=first_p_evt.magnitude,
                    rms_amplitude=first_p_evt.rms_amplitude,
                    energy=first_p_evt.energy,
                    duration_ms=first_p_evt.duration_ms,
                    frequency_hz=first_p_evt.frequency_hz,
                    sample_count=first_p_evt.sample_count,
                    features_dict=first_p_evt.features,
                ),
                baseline=baseline_trace,
                anomaly=AnomalyEvaluationTrace(
                    evaluated=baseline is not None,
                    is_anomalous=primary_res.is_anomalous,
                    magnitude_z_score=primary_res.magnitude_z_score,
                    energy_z_score=primary_res.energy_z_score,
                    magnitude_anomalous=(
                        abs(primary_res.magnitude_z_score) >= 3.0
                        if primary_res.magnitude_z_score is not None
                        else False
                    ),
                    energy_anomalous=(
                        abs(primary_res.energy_z_score) >= 3.0
                        if primary_res.energy_z_score is not None
                        else False
                    ),
                    z_threshold=3.0,
                    severity=primary_res.severity,
                    reasons=primary_res.anomaly_reasons,
                ),
                persistence=PersistenceTrace(
                    evaluated=True,
                    is_persistent=persistence_res.is_persistent,
                    total_events_in_window=persistence_res.total_events,
                    anomalous_events_in_window=persistence_res.anomalous_events,
                    anomaly_ratio=persistence_res.anomaly_ratio,
                    max_consecutive_anomalies=persistence_res.max_consecutive_anomalies,
                    window_duration_seconds=persistence_res.window_duration_seconds,
                    min_anomaly_count_required=persistence_res.min_anomaly_count_used,
                    min_anomaly_ratio_required=persistence_res.min_anomaly_ratio_used,
                    reasons=list(persistence_res.reasons),
                ),
                correlation=CorrelationTrace(
                    evaluated=True,
                    is_cross_sensor_correlated=is_cross_sensor,
                    correlated_group_id=primary_group.group_id if primary_group else None,
                    participating_sensors=list(primary_group.participating_sensors) if primary_group else [payload.sensor_id],
                    event_ids=[int(eid) for eid in primary_group.event_ids] if primary_group else [primary_res.event_id],
                    temporal_spread_ms=primary_group.temporal_spread_ms if primary_group else 0.0,
                    tolerance_seconds=0.025,
                    relative_source_hint=primary_group.relative_source_hint if primary_group else None,
                    reasons=[primary_group.relative_source_hint] if (primary_group and primary_group.relative_source_hint) else (
                        ["Multi-sensor cross-sensor correlation confirmed"] if is_cross_sensor else ["Single sensor localized excitation"]
                    ),
                ),
                trend=TrendTrace(
                    evaluated=True,
                    overall_trend=health_res.trend,
                    reasons=[f"Health trend classification: {health_res.trend}"],
                ),
                health=HealthTrace(
                    evaluated=True,
                    health_score=health_res.score,
                    health_status=health_res.status,
                    trend=health_res.trend,
                    deductions=health_res.deductions.to_dict() if hasattr(health_res.deductions, "to_dict") else None,
                    reason=health_res.reason,
                    evidence_summary=list(health_res.evidence_summary),
                ),
                alert=AlertTrace(
                    alert_generated=alert_generated,
                    alert_id=alert_id,
                    alert_severity=alert_sev,
                    alert_status=AlertStatus.ACTIVE if alert_generated else None,
                    alert_title=alert_title,
                    alert_message=health_res.reason if alert_generated else None,
                    timestamp=ref_time if alert_generated else None,
                ),
            )
            _set_processing_trace(trace_resp)
            for evt in event_results:
                _set_processing_trace_alias(str(evt.event_id), trace_resp)

            # 10. PROCESSING COMPLETED
            _emit_pipeline_event(
                LiveEventType.PROCESSING_COMPLETED,
                status="completed",
                trace_id=trace_id,
                event_id=primary_res.event_id,
                sensor_id=payload.sensor_id,
                zone_id=zone.id,
                zone_name=zone.name,
                sequence=payload.sequence,
                summary=msg,
            )

            return res

        except Exception as exc:
            _emit_pipeline_event(
                LiveEventType.PROCESSING_ERROR,
                stage=active_stage,
                status="error",
                trace_id=current_trace_id,
                sensor_id=payload.sensor_id,
                sequence=payload.sequence,
                error_message=str(exc),
                summary=f"Processing error in stage {active_stage.value}: {exc}",
            )
            raise

    def get_processing_trace(self, identifier: str) -> Optional[ProcessingTraceResponse]:
        """
        Retrieve a detailed processing trace by identifier (trace_id, event_id, sensor_id, or 'latest').

        If not cached in memory, reconstructs the trace from database records without rerunning signal processing.
        """
        key = identifier.strip()

        # 1. In-memory cached trace lookup
        cached = _get_cached_processing_trace(key)
        if cached is not None:
            return cached

        # 2. Database event lookup by integer ID
        db_event: Optional[Event] = None
        if key.isdigit():
            db_event = self.db.query(Event).filter(Event.id == int(key)).first()
        elif key.lower() == "latest":
            db_event = self.db.query(Event).order_by(Event.timestamp.desc(), Event.id.desc()).first()
        else:
            # Check by sensor_id
            db_event = (
                self.db.query(Event)
                .filter(Event.source_id == key)
                .order_by(Event.timestamp.desc(), Event.id.desc())
                .first()
            )

        if not db_event:
            return None

        # Reconstruct trace from database records
        zone = self.db.query(Zone).filter(Zone.id == db_event.zone_id).first()
        if not zone:
            return None

        baseline = self.baseline_repository.get_latest_for_zone(db_event.zone_id)
        meta = db_event.metadata_json or {}
        sample_rate = float(meta.get("sample_rate_hz", 1000.0))
        sequence = meta.get("sequence")
        sample_count = int(meta.get("sample_count", 0))
        det_threshold = float(meta.get("detection_threshold", 1.0))
        rms_amp = float(meta.get("rms_amplitude", 0.0))

        # Anomaly evaluation
        is_anom = False
        z_mag = None
        z_eng = None
        reasons: List[str] = []
        if baseline:
            try:
                anom_res = self.anomaly_service.analyze_event_by_id(db_event.id)
                is_anom = anom_res.is_anomalous
                z_mag = anom_res.magnitude_z_score
                z_eng = anom_res.energy_z_score
                reasons = list(anom_res.reasons)
            except Exception:
                pass

        # Persistence evaluation
        persistence_res = self.correlation_service.evaluate_zone_persistence(
            zone_id=db_event.zone_id,
            reference_time=db_event.timestamp,
            window_duration_seconds=300.0,
        )

        # Correlation evaluation
        corr_groups = self.correlation_service.correlate_zone_events(
            zone_id=db_event.zone_id,
            valid_from=db_event.timestamp - timedelta(seconds=300),
            valid_until=db_event.timestamp,
        )
        is_cross_sensor = any(g.is_cross_sensor for g in corr_groups)
        target_group = next((g for g in corr_groups if db_event.id in g.event_ids), None)

        # Health snapshot
        snapshot = (
            self.db.query(HealthSnapshot)
            .filter(HealthSnapshot.zone_id == db_event.zone_id, HealthSnapshot.timestamp <= db_event.timestamp)
            .order_by(HealthSnapshot.timestamp.desc(), HealthSnapshot.id.desc())
            .first()
        )

        # Alert
        alert = (
            self.db.query(Alert)
            .filter(Alert.zone_id == db_event.zone_id, Alert.timestamp == db_event.timestamp)
            .order_by(Alert.id.desc())
            .first()
        )

        trace_id = f"trace-evt-{db_event.id}"
        return ProcessingTraceResponse(
            metadata=TraceMetadata(
                trace_id=trace_id,
                event_id=db_event.id,
                sensor_id=db_event.source_id,
                zone_id=zone.id,
                zone_name=zone.name,
                timestamp=db_event.timestamp,
                sequence=sequence,
                sample_rate_hz=sample_rate,
                samples_count=sample_count,
                session_id=db_event.session_id,
            ),
            ingestion=RawTelemetryTrace(
                sensor_id=db_event.source_id,
                zone_name=zone.name,
                timestamp=db_event.timestamp,
                sample_rate_hz=sample_rate,
                samples_count=sample_count,
                sequence=sequence,
                samples_bounded=[],
                peak_amplitude=db_event.magnitude,
                rms_amplitude=rms_amp,
                is_bounded=True,
            ),
            conditioning=ConditioningTrace(
                dc_removal_applied=True,
                dc_offset_removed=None,
                filter_applied=True,
                filter_type="MOVING_AVERAGE",
                filter_window_size=3 if sample_count >= 5 else None,
                conditioned_samples_bounded=None,
            ),
            event_detection=EventDetectionTrace(
                detection_threshold=det_threshold,
                events_detected_count=1,
                events_detected=True,
                min_duration_samples=1,
                merge_gap_samples=2,
                detected_windows=[],
            ),
            features=FeatureExtractionTrace(
                event_id=db_event.id,
                peak_amplitude=db_event.magnitude,
                rms_amplitude=rms_amp,
                energy=db_event.energy,
                duration_ms=db_event.duration_ms,
                frequency_hz=db_event.frequency_hz,
                sample_count=sample_count,
                features_dict=meta,
            ),
            baseline=BaselineTrace(
                baseline_id=baseline.id if baseline else None,
                zone_id=zone.id,
                mean_magnitude=baseline.mean_magnitude if baseline else None,
                std_magnitude=baseline.std_magnitude if baseline else None,
                mean_energy=baseline.mean_energy if baseline else None,
                std_energy=baseline.std_energy if baseline else None,
                normal_event_rate=baseline.normal_event_rate if baseline else None,
                valid_from=baseline.valid_from if baseline else None,
                valid_until=baseline.valid_until if baseline else None,
                baseline_available=baseline is not None,
            ),
            anomaly=AnomalyEvaluationTrace(
                evaluated=baseline is not None,
                is_anomalous=is_anom,
                magnitude_z_score=z_mag,
                energy_z_score=z_eng,
                magnitude_anomalous=abs(z_mag) >= 3.0 if z_mag is not None else False,
                energy_anomalous=abs(z_eng) >= 3.0 if z_eng is not None else False,
                z_threshold=3.0,
                severity=db_event.severity,
                reasons=reasons,
            ),
            persistence=PersistenceTrace(
                evaluated=True,
                is_persistent=persistence_res.is_persistent,
                total_events_in_window=persistence_res.total_events,
                anomalous_events_in_window=persistence_res.anomalous_events,
                anomaly_ratio=persistence_res.anomaly_ratio,
                max_consecutive_anomalies=persistence_res.max_consecutive_anomalies,
                window_duration_seconds=persistence_res.window_duration_seconds,
                min_anomaly_count_required=persistence_res.min_anomaly_count_used,
                min_anomaly_ratio_required=persistence_res.min_anomaly_ratio_used,
                reasons=list(persistence_res.reasons),
            ),
            correlation=CorrelationTrace(
                evaluated=True,
                is_cross_sensor_correlated=is_cross_sensor,
                correlated_group_id=target_group.group_id if target_group else None,
                participating_sensors=list(target_group.participating_sensors) if target_group else [db_event.source_id],
                event_ids=[int(eid) for eid in target_group.event_ids] if target_group else [db_event.id],
                temporal_spread_ms=target_group.temporal_spread_ms if target_group else 0.0,
                tolerance_seconds=0.025,
                relative_source_hint=target_group.relative_source_hint if target_group else None,
                reasons=[target_group.relative_source_hint] if (target_group and target_group.relative_source_hint) else (
                    ["Multi-sensor cross-sensor correlation confirmed"] if is_cross_sensor else ["Single sensor localized excitation"]
                ),
            ),
            trend=TrendTrace(
                evaluated=snapshot is not None,
                overall_trend=snapshot.trend.value if snapshot and snapshot.trend else None,
                reasons=[f"Trend: {snapshot.trend.value}"] if snapshot and snapshot.trend else [],
            ),
            health=HealthTrace(
                evaluated=snapshot is not None,
                health_score=snapshot.score if snapshot else None,
                health_status=snapshot.status if snapshot else None,
                trend=snapshot.trend.value if snapshot and snapshot.trend else None,
                deductions=None,
                reason=snapshot.reason if snapshot else None,
                evidence_summary=[],
            ),
            alert=AlertTrace(
                alert_generated=alert is not None,
                alert_id=alert.id if alert else None,
                alert_severity=alert.severity if alert else None,
                alert_status=alert.status if alert else None,
                alert_title=alert.title if alert else None,
                alert_message=alert.message if alert else None,
                timestamp=alert.timestamp if alert else None,
            ),
        )

