import json
import os
from pathlib import Path
import sys
import time
import urllib.request

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from simulator.sensors.virtual_pzt import VirtualPZTSensor

def post_tel(payload):
    req = urllib.request.Request(
        "http://127.0.0.1:8000/api/v1/telemetry",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}
    )
    return json.loads(urllib.request.urlopen(req).read().decode())

def get_trace(ident):
    req = urllib.request.Request(f"http://127.0.0.1:8000/api/v1/telemetry/{ident}/processing-trace")
    return json.loads(urllib.request.urlopen(req).read().decode())

s1 = VirtualPZTSensor("PZT-Z05")

# 1. Healthy Telemetry
h_payload = s1.generate_physics_payload(mode="normal")
h_res = post_tel(h_payload)
h_peak = max(abs(x) for x in h_payload["samples"])
print("HEALTHY RUN:")
print("  HTTP: 200")
print("  Status:", h_res["status"])
print("  Events:", h_res["events_detected"])
print(f"  Sim Peak: {h_peak:.4f}")
print("  Health SHI:", h_res.get("health_score"))
print("  Alert:", h_res.get("alert_generated"))

# 2. Damaged Telemetry (Batch 1)
d_payload = s1.generate_physics_payload(mode="anomaly")
d_res = post_tel(d_payload)
d_peak = max(abs(x) for x in d_payload["samples"])
print("\nDAMAGED RUN (Batch 1):")
print("  HTTP: 200")
print("  Status:", d_res["status"])
print("  Events:", d_res["events_detected"])
print(f"  Sim Peak: {d_peak:.4f}")
print("  Anomaly:", any(e["is_anomalous"] for e in d_res["events"]))
print("  Persistence:", d_res["temporal_persistence_confirmed"])
print("  Health SHI:", d_res.get("health_score"), f"({d_res.get('health_status')})")
print("  Alert:", d_res.get("alert_generated"))

# 3. Damaged Telemetry (Batch 2 - Persistence & Alert)
time.sleep(0.5)
d_payload2 = s1.generate_physics_payload(mode="anomaly")
d_res2 = post_tel(d_payload2)
print("\nDAMAGED RUN (Batch 2):")
print("  Status:", d_res2["status"])
print("  Persistence:", d_res2["temporal_persistence_confirmed"])
print("  Health SHI:", d_res2.get("health_score"), f"({d_res2.get('health_status')})")
print("  Alert:", d_res2.get("alert_generated"), "ID:", d_res2.get("alert_id"), "Severity:", d_res2.get("alert_severity"))

# 4. Processing Inspector Trace Check
trace = get_trace("latest")
print("\nPROCESSING TRACE CHECK:")
print("  Trace ID:", trace["metadata"]["trace_id"])
print("  Sensor ID:", trace["metadata"]["sensor_id"])
print("  Raw Ingest Peak:", trace["ingestion"]["peak_amplitude"])
print("  Events Detected:", trace["event_detection"]["events_detected"])
print("  Anomaly Flag:", trace["anomaly"]["is_anomalous"])
print("  Health Score:", trace["health"]["health_score"])
print("  Alert Generated:", trace["alert"]["alert_generated"])

# 5. BIM GLB Node Mapping Check
with open("data/processed/bim/sensor_registry.json") as f:
    registry = json.load(f)
sensor_match = [s for s in registry["sensors"] if s["sensor_id"] == "PZT-Z05"][0]

with open("data/processed/bim/glb_mapping.json") as f:
    glb_map = json.load(f)

# Look up glb_node by matching ifc_guid
glb_node = None
for k, v in glb_map.items():
    if v.get("ifc_guid") == sensor_match["component_guid"]:
        glb_node = v.get("glb_node")
        break

print("\nBIM LOCALIZATION CHECK:")
print("  Sensor:", sensor_match["sensor_id"])
print("  IFC GUID:", sensor_match["component_guid"])
print("  Component Name:", sensor_match["component_name"])
print("  GLB Node:", glb_node)
print("  Storey:", sensor_match["storey"])
print("  Zone:", sensor_match["zone_name"])

