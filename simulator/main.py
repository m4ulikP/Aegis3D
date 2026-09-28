"""Aegis3D Virtual Sensor Simulator CLI.

Standalone application representing PZT sensor nodes, generating representative
sampled telemetry, and dispatching payloads to the Aegis3D backend API.
"""

import argparse
from datetime import datetime, timezone
import os
import sys
import time
from typing import Optional

# Ensure simulator directory and parent are discoverable on sys.path
_current_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.abspath(os.path.join(_current_dir, ".."))
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

try:
    from simulator.client import TelemetryClient, TelemetryClientResult
    from simulator.config import (
        DEFAULT_SENSOR_ZONE_MAP,
        ZONE_MAIN_DECK,
        ZONE_SUBSTRUCTURE,
        SimulatorConfig,
    )
    from simulator.sensors.virtual_pzt import VirtualPZTSensor
    from simulator.signal_generator import generate_correlated_pair
except ImportError:
    from client import TelemetryClient, TelemetryClientResult
    from config import (
        DEFAULT_SENSOR_ZONE_MAP,
        ZONE_MAIN_DECK,
        ZONE_SUBSTRUCTURE,
        SimulatorConfig,
    )
    from sensors.virtual_pzt import VirtualPZTSensor
    from signal_generator import generate_correlated_pair


def print_banner() -> None:
    """Display startup header."""
    print("=" * 72)
    print("  AEGIS3D — VIRTUAL PZT SENSOR SIMULATOR")
    print("  Software-First Representative Telemetry Generator")
    print("=" * 72)


def format_client_result(
    sensor_id: str,
    zone_name: str,
    mode: str,
    sequence: int,
    sample_count: int,
    sample_rate_hz: float,
    sim_peak: float,
    result: TelemetryClientResult,
    target_url: str,
) -> None:
    """Print readable terminal output separating simulation metrics from backend decisions."""
    now_str = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"\n[{now_str}] Sensor: {sensor_id} | Zone: {zone_name}")
    print(f"  Simulation -> Mode: {mode.upper()} | Seq: {sequence} | Samples: {sample_count} ({sample_rate_hz:.1f} Hz) | Sim Peak: {sim_peak:.3f}")

    if result.success:
        print(f"  HTTP POST  -> {target_url} [HTTP {result.status_code} OK]")
        print(f"  Backend    -> Status: {result.backend_status}")
        print(f"  Detection  -> Events Detected: {result.events_detected} | Persistence: {result.temporal_persistence_confirmed} | Correlation: {result.cross_sensor_correlation_confirmed}")

        if result.health_score is not None:
            print(f"  Health SHI -> Score: {result.health_score:.1f}/100 ({result.health_status})")
        if result.alert_generated:
            print(f"  Alert      -> [ACTIVE ALERT] Severity: {result.alert_severity}")

        if result.message:
            print(f"  Message    -> {result.message}")
    else:
        print(f"  HTTP POST  -> {target_url} [FAILED: HTTP {result.status_code}]")
        print(f"  Error      -> {result.error_message}")


def run_single_sensor_loop(
    sensor: VirtualPZTSensor,
    client: TelemetryClient,
    mode: str,
    sample_count: int,
    batches: int,
    interval_seconds: float,
    seed: Optional[int] = None,
) -> None:
    """Execute telemetry generation loop for a single virtual sensor."""
    batch_idx = 0
    consecutive_errors = 0

    print(f"\nStarting Telemetry Stream:")
    print(f"  Target: {client.full_url}")
    print(f"  Sensor: {sensor.sensor_id} ({sensor.zone_name})")
    print(f"  Mode:   {mode.upper()} | Batches: {batches if batches > 0 else 'Continuous'} | Interval: {interval_seconds}s")
    print("-" * 72)

    try:
        while True:
            batch_idx += 1
            batch_seed = (seed + batch_idx) if seed is not None else None

            # Generate payload (pure telemetry samples, zero forced backend decisions)
            payload = sensor.generate_payload(
                mode=mode,
                sample_count=sample_count,
                seed=batch_seed,
            )

            # Compute local simulation peak for debug display
            sim_peak = max(abs(x) for x in payload["samples"]) if payload["samples"] else 0.0

            # Send payload via HTTP
            result = client.send_telemetry(payload)

            format_client_result(
                sensor_id=sensor.sensor_id,
                zone_name=sensor.zone_name,
                mode=mode,
                sequence=payload["sequence"],
                sample_count=sample_count,
                sample_rate_hz=sensor.sample_rate_hz,
                sim_peak=sim_peak,
                result=result,
                target_url=client.full_url,
            )

            if not result.success:
                consecutive_errors += 1
                if consecutive_errors >= 5:
                    print("\n[WARNING] 5 consecutive failures contacting backend. Check network connectivity or FastAPI status.")
            else:
                consecutive_errors = 0

            if batches > 0 and batch_idx >= batches:
                break

            time.sleep(interval_seconds)

    except KeyboardInterrupt:
        print("\n\n[INFO] Simulator interrupted by user. Exiting cleanly.")


def run_correlation_demo(
    client: TelemetryClient,
    sample_count: int,
    batches: int,
    interval_seconds: float,
    seed: Optional[int] = None,
) -> None:
    """
    Demonstrate 2-PZT cross-sensor correlation across PZT-Z1-01 and PZT-Z1-02 in Zone 1.

    Generates temporally related acoustic stress signals:
    - PZT-Z1-01 receives primary burst wave first.
    - PZT-Z1-02 receives secondary burst delayed by 5ms (< 25ms backend tolerance window).
    """
    sensor1 = VirtualPZTSensor(sensor_id="PZT-Z1-01", zone_name=ZONE_MAIN_DECK)
    sensor2 = VirtualPZTSensor(sensor_id="PZT-Z1-02", zone_name=ZONE_MAIN_DECK)

    print(f"\nStarting 2-PZT Cross-Sensor Correlation Demo:")
    print(f"  Target:    {client.full_url}")
    print(f"  Zone:      {ZONE_MAIN_DECK}")
    print(f"  Sensors:   PZT-Z1-01 (Primary) and PZT-Z1-02 (Secondary, +5ms TDOA)")
    print(f"  Batches:   {batches if batches > 0 else 'Continuous'} | Interval: {interval_seconds}s")
    print("-" * 72)

    batch_idx = 0
    try:
        while True:
            batch_idx += 1
            batch_seed = (seed + batch_idx) if seed is not None else None

            # Generate physically coordinated wave signals
            s1_samples, s2_samples, tdoa_sec = generate_correlated_pair(
                sample_count=sample_count,
                sample_rate_hz=sensor1.sample_rate_hz,
                peak_amp=4.5,
                tdoa_seconds=0.005,  # 5ms propagation delay
                attenuation=0.85,
                seed=batch_seed,
            )

            # Common base timestamp
            now_utc = datetime.now(timezone.utc)

            # Payload 1: Sensor 1
            payload1 = sensor1.generate_payload(
                samples=s1_samples,
                timestamp=now_utc,
            )
            sim_peak1 = max(abs(x) for x in s1_samples)
            res1 = client.send_telemetry(payload1)

            format_client_result(
                sensor_id=sensor1.sensor_id,
                zone_name=sensor1.zone_name,
                mode="CORRELATION (PZT 1/2)",
                sequence=payload1["sequence"],
                sample_count=sample_count,
                sample_rate_hz=sensor1.sample_rate_hz,
                sim_peak=sim_peak1,
                result=res1,
                target_url=client.full_url,
            )

            # Payload 2: Sensor 2
            payload2 = sensor2.generate_payload(
                samples=s2_samples,
                timestamp=now_utc,
            )
            sim_peak2 = max(abs(x) for x in s2_samples)
            res2 = client.send_telemetry(payload2)

            format_client_result(
                sensor_id=sensor2.sensor_id,
                zone_name=sensor2.zone_name,
                mode="CORRELATION (PZT 2/2)",
                sequence=payload2["sequence"],
                sample_count=sample_count,
                sample_rate_hz=sensor2.sample_rate_hz,
                sim_peak=sim_peak2,
                result=res2,
                target_url=client.full_url,
            )

            if res2.cross_sensor_correlation_confirmed:
                print("\n  >>> [SUCCESS] 2-PZT Cross-Sensor Correlation Confirmed by Backend Engine! <<<")

            if batches > 0 and batch_idx >= batches:
                break

            time.sleep(interval_seconds)

    except KeyboardInterrupt:
        print("\n\n[INFO] Correlation demo interrupted by user. Exiting cleanly.")


def parse_arguments() -> argparse.Namespace:
    """Configure and parse CLI command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Aegis3D Virtual Sensor Simulator — Generates representative PZT telemetry."
    )
    parser.add_argument(
        "--mode",
        choices=["normal", "transient", "anomaly", "correlation"],
        default="normal",
        help="Telemetry simulation mode (default: normal)",
    )
    parser.add_argument(
        "--sensor",
        default="PZT-Z1-01",
        help="Sensor identifier (default: PZT-Z1-01)",
    )
    parser.add_argument(
        "--zone",
        default=None,
        help="Structural zone name override (default: auto-inferred from sensor ID)",
    )
    parser.add_argument(
        "--backend-url",
        default=None,
        help="FastAPI backend URL (e.g. http://localhost:8000 or http://192.168.1.50:8000)",
    )
    parser.add_argument(
        "--batches",
        type=int,
        default=1,
        help="Number of telemetry batches to transmit (default: 1, 0 or negative for continuous)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Interval delay in seconds between telemetry batches (default: 1.0)",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=1000,
        help="Number of discrete samples per telemetry batch (default: 1000)",
    )
    parser.add_argument(
        "--sample-rate",
        type=float,
        default=1000.0,
        help="Sampling rate in Hertz (default: 1000.0)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional RNG integer seed for deterministic signal reproduction",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=5.0,
        help="HTTP request timeout in seconds (default: 5.0)",
    )

    return parser.parse_args()


def main() -> int:
    """CLI execution entrypoint."""
    args = parse_arguments()
    print_banner()

    # Load configuration
    config = SimulatorConfig.from_env()
    if args.backend_url:
        config.backend_url = args.backend_url.rstrip("/")
    if args.timeout:
        config.timeout_seconds = args.timeout

    client = TelemetryClient(
        backend_url=config.backend_url,
        endpoint=config.telemetry_endpoint,
        timeout_seconds=config.timeout_seconds,
    )

    if args.mode == "correlation":
        run_correlation_demo(
            client=client,
            sample_count=args.samples,
            batches=args.batches,
            interval_seconds=args.interval,
            seed=args.seed,
        )
    else:
        sensor = VirtualPZTSensor(
            sensor_id=args.sensor,
            zone_name=args.zone,
            sample_rate_hz=args.sample_rate,
        )
        run_single_sensor_loop(
            sensor=sensor,
            client=client,
            mode=args.mode,
            sample_count=args.samples,
            batches=args.batches,
            interval_seconds=args.interval,
            seed=args.seed,
        )

    print("\n[INFO] Simulation session finished.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
