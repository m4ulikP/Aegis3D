from enum import Enum


class SessionMode(str, Enum):
    LIVE = "LIVE"
    SIMULATION = "SIMULATION"
    REPLAY = "REPLAY"


class SessionStatus(str, Enum):
    PLANNED = "PLANNED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class EventSourceType(str, Enum):
    SIMULATOR = "SIMULATOR"
    SENSOR = "SENSOR"
    IMPORTED = "IMPORTED"


class EventSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class EventStatus(str, Enum):
    DETECTED = "DETECTED"
    REVIEWED = "REVIEWED"
    DISMISSED = "DISMISSED"


class HealthStatus(str, Enum):
    NORMAL = "NORMAL"
    MONITOR = "MONITOR"
    INSPECTION_ADVISED = "INSPECTION_ADVISED"
    HIGH_PRIORITY_INSPECTION = "HIGH_PRIORITY_INSPECTION"


class HealthTrend(str, Enum):
    STABLE = "STABLE"
    INCREASING = "INCREASING"
    DECREASING = "DECREASING"


class AlertSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertStatus(str, Enum):
    ACTIVE = "ACTIVE"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"
