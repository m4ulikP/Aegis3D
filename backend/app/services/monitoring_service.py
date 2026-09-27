"""Service layer handling zone management, alert queries, and dashboard health summaries."""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.enums import AlertSeverity, AlertStatus, EventSeverity, EventStatus, HealthStatus, HealthTrend
from app.models.event import Event
from app.models.health import HealthSnapshot
from app.models.zone import Zone
from app.schemas.alert import AlertResponse
from app.schemas.health import HealthSummaryResponse
from app.schemas.zone import (
    CorrelatedGroupSchema,
    PeriodMetricsSchema,
    TemporalPersistenceSchema,
    ZoneCorrelationResponse,
    ZoneDetailResponse,
    ZoneHealthResponse,
    ZoneTrendResponse,
)
from app.services.correlation_service import CorrelationService
from app.services.health_service import HealthService
from app.services.trend_service import TrendService
from app.trend.types import TrendDirection


class ZoneNotFoundError(Exception):
    """Raised when a requested Zone does not exist."""

    pass


class MonitoringService:
    """Service encapsulating zone monitoring queries, health aggregation, and alert listing."""

    def __init__(
        self,
        db: Session,
        health_service: Optional[HealthService] = None,
        trend_service: Optional[TrendService] = None,
        correlation_service: Optional[CorrelationService] = None,
    ) -> None:
        self.db = db
        self.health_service = health_service or HealthService(db)
        self.trend_service = trend_service or TrendService(db)
        self.correlation_service = correlation_service or CorrelationService(db)

    def get_all_zones(self) -> List[Zone]:
        """Retrieve all zones ordered by ID."""
        return self.db.query(Zone).order_by(Zone.id.asc()).all()

    def get_zone_by_id(self, zone_id: int) -> Zone:
        """Retrieve a zone by ID or raise ZoneNotFoundError."""
        zone = self.db.query(Zone).filter(Zone.id == zone_id).first()
        if not zone:
            raise ZoneNotFoundError(f"Zone with id {zone_id} not found")
        return zone

    def get_zone_detail(self, zone_id: int) -> ZoneDetailResponse:
        """Retrieve zone detail metadata including event and alert counts."""
        zone = self.get_zone_by_id(zone_id)

        event_count = self.db.query(func.count(Event.id)).filter(Event.zone_id == zone_id).scalar() or 0
        active_alert_count = (
            self.db.query(func.count(Alert.id))
            .filter(Alert.zone_id == zone_id, Alert.status == AlertStatus.ACTIVE)
            .scalar()
            or 0
        )

        latest_snapshot = (
            self.db.query(HealthSnapshot)
            .filter(HealthSnapshot.zone_id == zone_id)
            .order_by(HealthSnapshot.timestamp.desc())
            .first()
        )
        latest_health_status = latest_snapshot.status if latest_snapshot else HealthStatus.NORMAL

        return ZoneDetailResponse(
            id=zone.id,
            name=zone.name,
            floor=zone.floor,
            description=zone.description,
            created_at=zone.created_at,
            event_count=event_count,
            active_alert_count=active_alert_count,
            latest_health_status=latest_health_status,
        )

    def get_zone_events(
        self,
        zone_id: int,
        limit: int = 50,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        severity: Optional[EventSeverity] = None,
        status: Optional[EventStatus] = None,
    ) -> List[Event]:
        """Retrieve events associated with a zone with filtering and pagination."""
        self.get_zone_by_id(zone_id)

        query = self.db.query(Event).filter(Event.zone_id == zone_id)

        if start_time:
            query = query.filter(Event.timestamp >= start_time)
        if end_time:
            query = query.filter(Event.timestamp <= end_time)
        if severity:
            query = query.filter(Event.severity == severity)
        if status:
            query = query.filter(Event.status == status)

        return query.order_by(Event.timestamp.desc()).limit(limit).all()

    def get_zone_health(
        self,
        zone_id: int,
        reference_time: Optional[datetime] = None,
        window_duration_seconds: float = 3600.0,
    ) -> ZoneHealthResponse:
        """Evaluate and return the latest Structural Health Indicator for a zone."""
        self.get_zone_by_id(zone_id)

        result = self.health_service.evaluate_zone_health(
            zone_id=zone_id,
            reference_time=reference_time,
            window_duration_seconds=window_duration_seconds,
        )

        trend_map = {
            "STABLE": HealthTrend.STABLE,
            "INCREASING": HealthTrend.INCREASING,
            "DECREASING": HealthTrend.DECREASING,
            "INSUFFICIENT_DATA": HealthTrend.STABLE,
        }
        health_trend = trend_map.get(str(result.trend), HealthTrend.STABLE)

        status_map = {
            "NORMAL": HealthStatus.NORMAL,
            "MONITOR": HealthStatus.MONITOR,
            "INSPECTION_ADVISED": HealthStatus.INSPECTION_ADVISED,
            "HIGH_PRIORITY_INSPECTION": HealthStatus.HIGH_PRIORITY_INSPECTION,
        }
        health_status = status_map.get(str(result.status), HealthStatus.NORMAL)

        return ZoneHealthResponse(
            zone_id=zone_id,
            score=result.score,
            status=health_status,
            trend=health_trend,
            reason=result.reason,
            timestamp=result.timestamp,
            evidence=result.to_dict(),
        )

    def get_zone_trend(
        self,
        zone_id: int,
        reference_time: Optional[datetime] = None,
        analysis_window_seconds: float = 3600.0,
    ) -> ZoneTrendResponse:
        """Expose existing deterministic trend analysis for a zone."""
        self.get_zone_by_id(zone_id)

        trend_res = self.trend_service.evaluate_zone_trend(
            zone_id=zone_id,
            reference_time=reference_time,
            analysis_window_seconds=analysis_window_seconds,
        )

        trend_dir_str = (
            trend_res.overall_trend_direction.value
            if hasattr(trend_res.overall_trend_direction, "value")
            else str(trend_res.overall_trend_direction)
        )

        is_significant = trend_res.overall_trend_direction in [
            TrendDirection.INCREASING,
            TrendDirection.DECREASING,
        ]

        reason_str = "; ".join(trend_res.reasons) if trend_res.reasons else "Trend evaluation complete"

        return ZoneTrendResponse(
            zone_id=zone_id,
            overall_trend_direction=trend_dir_str,
            event_rate_change_ratio=trend_res.anomaly_rate_delta,
            magnitude_delta=trend_res.magnitude_delta or 0.0,
            is_statistically_significant=is_significant,
            reason=reason_str,
            earlier_period=PeriodMetricsSchema(
                total_events=trend_res.earlier_period.total_events,
                anomalous_events=trend_res.earlier_period.anomalous_events,
                anomaly_rate=trend_res.earlier_period.anomaly_rate,
                mean_magnitude=trend_res.earlier_period.mean_magnitude,
                persistent_anomaly_count=trend_res.earlier_period.persistent_anomaly_count,
                cross_sensor_event_count=trend_res.earlier_period.cross_sensor_event_count,
            ),
            later_period=PeriodMetricsSchema(
                total_events=trend_res.later_period.total_events,
                anomalous_events=trend_res.later_period.anomalous_events,
                anomaly_rate=trend_res.later_period.anomaly_rate,
                mean_magnitude=trend_res.later_period.mean_magnitude,
                persistent_anomaly_count=trend_res.later_period.persistent_anomaly_count,
                cross_sensor_event_count=trend_res.later_period.cross_sensor_event_count,
            ),
        )

    def get_zone_correlation(
        self,
        zone_id: int,
        reference_time: Optional[datetime] = None,
        window_duration_seconds: float = 300.0,
        tolerance_seconds: float = 0.025,
    ) -> ZoneCorrelationResponse:
        """Expose temporal persistence and two-PZT cross-sensor correlation for a zone."""
        self.get_zone_by_id(zone_id)

        ref_t = reference_time or datetime.now(timezone.utc)
        if ref_t.tzinfo is None:
            ref_t = ref_t.replace(tzinfo=timezone.utc)

        persistence_res = self.correlation_service.evaluate_zone_persistence(
            zone_id=zone_id,
            reference_time=ref_t,
            window_duration_seconds=window_duration_seconds,
        )

        start_t = ref_t - timedelta(seconds=window_duration_seconds)
        corr_groups = self.correlation_service.correlate_zone_events(
            zone_id=zone_id,
            valid_from=start_t,
            valid_until=ref_t,
            tolerance_seconds=tolerance_seconds,
        )

        group_schemas: List[CorrelatedGroupSchema] = []
        cross_sensor_count = 0
        for g in corr_groups:
            if g.is_cross_sensor:
                cross_sensor_count += 1
            group_schemas.append(
                CorrelatedGroupSchema(
                    group_id=g.group_id,
                    event_ids=[int(eid) for eid in g.event_ids if isinstance(eid, (int, float, str)) and str(eid).isdigit()],
                    temporal_spread_ms=g.temporal_spread_ms,
                    is_cross_sensor=g.is_cross_sensor,
                    relative_source_hint=g.relative_source_hint,
                )
            )

        return ZoneCorrelationResponse(
            zone_id=zone_id,
            temporal_persistence=TemporalPersistenceSchema(
                is_persistent=persistence_res.is_persistent,
                total_events=persistence_res.total_events,
                anomalous_events=persistence_res.anomalous_events,
                anomaly_ratio=persistence_res.anomaly_ratio,
                window_duration_seconds=persistence_res.window_duration_seconds,
            ),
            correlated_groups_count=len(corr_groups),
            cross_sensor_groups_count=cross_sensor_count,
            correlated_groups=group_schemas,
        )

    def get_alerts(
        self,
        zone_id: Optional[int] = None,
        status: Optional[AlertStatus] = None,
        severity: Optional[AlertSeverity] = None,
        limit: int = 50,
    ) -> List[Alert]:
        """Retrieve system alerts with optional filtering."""
        query = self.db.query(Alert)

        if zone_id is not None:
            query = query.filter(Alert.zone_id == zone_id)
        if status is not None:
            query = query.filter(Alert.status == status)
        if severity is not None:
            query = query.filter(Alert.severity == severity)

        return query.order_by(Alert.timestamp.desc()).limit(limit).all()

    def get_health_summary(self) -> HealthSummaryResponse:
        """Calculate high-level dashboard health summary across all zones."""
        total_zones = self.db.query(func.count(Zone.id)).scalar() or 0
        active_alerts = (
            self.db.query(func.count(Alert.id)).filter(Alert.status == AlertStatus.ACTIVE).scalar() or 0
        )
        recent_events = self.db.query(func.count(Event.id)).scalar() or 0

        subq = (
            self.db.query(
                HealthSnapshot.zone_id,
                func.max(HealthSnapshot.timestamp).label("max_ts"),
            )
            .group_by(HealthSnapshot.zone_id)
            .subquery()
        )

        snapshots = (
            self.db.query(HealthSnapshot)
            .join(
                subq,
                (HealthSnapshot.zone_id == subq.c.zone_id) & (HealthSnapshot.timestamp == subq.c.max_ts),
            )
            .all()
        )

        health_counts: Dict[str, int] = {
            HealthStatus.NORMAL.value: 0,
            HealthStatus.MONITOR.value: 0,
            HealthStatus.INSPECTION_ADVISED.value: 0,
            HealthStatus.HIGH_PRIORITY_INSPECTION.value: 0,
        }

        covered_zones = set()
        for snap in snapshots:
            status_val = snap.status.value if hasattr(snap.status, "value") else str(snap.status)
            health_counts[status_val] = health_counts.get(status_val, 0) + 1
            covered_zones.add(snap.zone_id)

        uncovered = total_zones - len(covered_zones)
        if uncovered > 0:
            health_counts[HealthStatus.NORMAL.value] += uncovered

        latest_event_ts = self.db.query(func.max(Event.timestamp)).scalar()
        latest_snap_ts = self.db.query(func.max(HealthSnapshot.timestamp)).scalar()

        latest_ts = None
        if latest_event_ts and latest_snap_ts:
            latest_ts = max(latest_event_ts, latest_snap_ts)
        elif latest_event_ts:
            latest_ts = latest_event_ts
        elif latest_snap_ts:
            latest_ts = latest_snap_ts

        return HealthSummaryResponse(
            total_zones=total_zones,
            health_status_counts=health_counts,
            active_alerts_count=active_alerts,
            recent_events_count=recent_events,
            latest_timestamp=latest_ts,
        )
