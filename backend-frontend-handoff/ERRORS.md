# Aegis3D API Error Behavior Reference

This document describes the actual HTTP error status codes, trigger conditions, and JSON error response structures produced by the Aegis3D FastAPI backend.

---

## Error Response Payload Structures

The backend returns standard FastAPI / Starlette JSON error structures:

### Single Error Detail (`HTTP 404`, `HTTP 500/503`)
```json
{
  "detail": "Zone with id 999999 not found"
}
```

### Complex Object Error Detail (`HTTP 503` Database Failure)
```json
{
  "detail": {
    "status": "error",
    "database": "unreachable"
  }
}
```

### Validation Error Detail (`HTTP 422 Unprocessable Entity`)
Produced automatically by FastAPI/Pydantic when path parameters, query parameters, or POST body payloads violate validation rules:
```json
{
  "detail": [
    {
      "type": "greater_than_equal",
      "loc": ["body", "magnitude"],
      "msg": "Input should be greater than or equal to 0",
      "input": -10.0,
      "ctx": { "ge": 0.0 }
    }
  ]
}
```

---

## Known Error Conditions

| HTTP Status | Condition / Endpoint | Detail Payload Example |
| :--- | :--- | :--- |
| `404 Not Found` | Nonexistent `zone_id` on any `/zones/{zone_id}` endpoint | `{"detail": "Zone with id 999999 not found"}` |
| `404 Not Found` | Nonexistent `event_id` on `GET /events/{event_id}` | `{"detail": "Event with id 999999 not found"}` |
| `404 Not Found` | Nonexistent `session_id` on `POST /events` | `{"detail": "MonitoringSession with id 999999 not found"}` |
| `422 Unprocessable Entity` | Negative magnitude, energy, or duration on `POST /events` | `{"detail": [...]}` (Pydantic validation array) |
| `422 Unprocessable Entity` | Invalid string enum value (e.g., `source_type="INVALID"`) | `{"detail": [...]}` (Pydantic validation array) |
| `422 Unprocessable Entity` | Query parameter constraint violation (`limit < 1` or `limit > 500`) | `{"detail": [...]}` |
| `503 Service Unavailable` | PostgreSQL database connection failure on `GET /health/db` | `{"detail": {"status": "error", "database": "unreachable"}}` |
