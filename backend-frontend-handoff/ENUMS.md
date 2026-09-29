# Aegis3D Backend Enum Reference

This document defines the exact string enum values used across the Aegis3D backend API. Frontend TypeScript definitions must match these exact string literals.

---

## 1. Structural Health Indicator Enums

### `HealthStatus`
Represents the structural health monitoring status category derived from the 0–100 SHI score.

```typescript
export type HealthStatus = 
  | "NORMAL"                   // Score >= 90.0
  | "MONITOR"                  // 70.0 <= Score < 90.0
  | "INSPECTION_ADVISED"       // 45.0 <= Score < 70.0
  | "HIGH_PRIORITY_INSPECTION" // Score < 45.0
```

### `HealthTrend`
Represents the directional structural health trend.

```typescript
export type HealthTrend = 
  | "STABLE"
  | "INCREASING"
  | "DECREASING"
```

---

## 2. Structural Observation Event Enums

### `EventSeverity`
Rating assigned to an individual structural observation event.

```typescript
export type EventSeverity = 
  | "LOW"
  | "MEDIUM"
  | "HIGH"
  | "CRITICAL"
```

### `EventStatus`
Workflow state of a structural event observation.

```typescript
export type EventStatus = 
  | "DETECTED"
  | "REVIEWED"
  | "DISMISSED"
```

### `EventSourceType`
Origin of the event measurement.

```typescript
export type EventSourceType = 
  | "SIMULATOR" // Synthetic simulation generator
  | "SENSOR"    // Physical or hardware transducer node
  | "IMPORTED"  // Dataset log file import
```

---

## 3. Actionable Alert Enums

### `AlertSeverity`
Severity rating of an actionable system alert.

```typescript
export type AlertSeverity = 
  | "LOW"
  | "MEDIUM"
  | "HIGH"
  | "CRITICAL"
```

### `AlertStatus`
Lifecycle state of an alert notification.

```typescript
export type AlertStatus = 
  | "ACTIVE"
  | "ACKNOWLEDGED"
  | "RESOLVED"
```

---

## 4. Monitoring Session Enums

### `SessionMode`
Operating mode of a monitoring session.

```typescript
export type SessionMode = 
  | "LIVE"
  | "SIMULATION"
  | "REPLAY"
```

### `SessionStatus`
Status of a monitoring session execution.

```typescript
export type SessionStatus = 
  | "PLANNED"
  | "RUNNING"
  | "COMPLETED"
  | "CANCELLED"
```
