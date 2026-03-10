#!/usr/bin/env python3
"""Run a full REST-based HIL end-to-end workflow."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run SmartWaterFactory HIL REST end-to-end demo.")
    parser.add_argument("--host", default="127.0.0.1", help="API host.")
    parser.add_argument("--port", type=int, default=5056, help="API port.")
    parser.add_argument("--username", default="admin", help="Login username.")
    parser.add_argument("--password", default="admin123", help="Login password.")
    parser.add_argument("--scenario", default="steady", help="Initial HIL scenario.")
    parser.add_argument("--steps-before-fault", type=int, default=3, help="Steps before fault injection.")
    parser.add_argument("--steps-after-fault", type=int, default=1, help="Steps after fault injection.")
    parser.add_argument("--coagulant-dose", type=float, default=6.0, help="Coagulant command.")
    parser.add_argument("--aeration-rate-ma", type=float, default=12.0, help="Aeration command in mA.")
    parser.add_argument("--fault-sensor", default="turbidity", help="Fault sensor name.")
    parser.add_argument("--fault-mode", default="stuck", help="Fault mode.")
    parser.add_argument("--fault-value", type=float, default=42.0, help="Fault fixed value.")
    parser.add_argument(
        "--output",
        default="outputs/hil_rest_e2e_summary.json",
        help="Path to write the JSON summary.",
    )
    parser.add_argument(
        "--reuse-server",
        action="store_true",
        help="Use an already running API server instead of spawning one.",
    )
    return parser


def _wait_for_health(base_url: str, timeout_s: float = 20.0) -> Dict[str, Any]:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            response = requests.get(f"{base_url}/api/health", timeout=1)
            if response.ok:
                return response.json()
        except Exception:
            time.sleep(0.5)
    raise RuntimeError("API server did not start in time")


def _spawn_server(host: str, port: int) -> subprocess.Popen[str]:
    server_code = (
        "from utils.api_server import APIConfig, WaterPlantAPIServer;"
        f"server = WaterPlantAPIServer(APIConfig(host='{host}', port={port}, debug=False, enable_websocket=False));"
        "server.run()"
    )
    return subprocess.Popen([sys.executable, "-c", server_code], cwd=PROJECT_ROOT)


def run_rest_e2e(
    *,
    host: str,
    port: int,
    username: str,
    password: str,
    scenario: str,
    steps_before_fault: int,
    steps_after_fault: int,
    coagulant_dose: float,
    aeration_rate_ma: float,
    fault_sensor: str,
    fault_mode: str,
    fault_value: float,
    reuse_server: bool = False,
) -> Dict[str, Any]:
    base_url = f"http://{host}:{port}"
    process = None
    try:
        if not reuse_server:
            process = _spawn_server(host, port)

        health = _wait_for_health(base_url)

        login = requests.post(
            f"{base_url}/api/auth/login",
            json={"username": username, "password": password},
            timeout=5,
        )
        login.raise_for_status()
        login_payload = login.json()
        token = login_payload["data"]["token"]
        headers = {"Authorization": f"Bearer {token}"}

        scenarios = requests.get(f"{base_url}/api/hil/scenarios", headers=headers, timeout=5)
        scenarios.raise_for_status()

        started = requests.post(
            f"{base_url}/api/hil/start",
            headers=headers,
            json={"scenario": scenario, "random_seed": 7, "dt_s": 1.0},
            timeout=5,
        )
        started.raise_for_status()
        started_payload = started.json()
        simulation_id = started_payload["data"]["simulation_id"]

        control = requests.post(
            f"{base_url}/api/hil/{simulation_id}/control",
            headers=headers,
            json={"coagulant_dose": coagulant_dose, "aeration_rate_ma": aeration_rate_ma},
            timeout=5,
        )
        control.raise_for_status()

        stepped = requests.post(
            f"{base_url}/api/hil/{simulation_id}/step",
            headers=headers,
            json={"steps": steps_before_fault},
            timeout=5,
        )
        stepped.raise_for_status()

        fault = requests.post(
            f"{base_url}/api/hil/{simulation_id}/fault",
            headers=headers,
            json={"sensor_name": fault_sensor, "mode": fault_mode, "value": fault_value},
            timeout=5,
        )
        fault.raise_for_status()

        stepped_after_fault = requests.post(
            f"{base_url}/api/hil/{simulation_id}/step",
            headers=headers,
            json={"steps": steps_after_fault},
            timeout=5,
        )
        stepped_after_fault.raise_for_status()

        status = requests.get(
            f"{base_url}/api/hil/{simulation_id}/status",
            headers=headers,
            timeout=5,
        )
        status.raise_for_status()

        return {
            "base_url": base_url,
            "health": health,
            "login": login_payload,
            "scenarios": scenarios.json(),
            "started": started_payload,
            "control": control.json(),
            "stepped": stepped.json(),
            "fault": fault.json(),
            "stepped_after_fault": stepped_after_fault.json(),
            "status": status.json(),
        }
    finally:
        if process is not None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    summary = run_rest_e2e(
        host=args.host,
        port=args.port,
        username=args.username,
        password=args.password,
        scenario=args.scenario,
        steps_before_fault=args.steps_before_fault,
        steps_after_fault=args.steps_after_fault,
        coagulant_dose=args.coagulant_dose,
        aeration_rate_ma=args.aeration_rate_ma,
        fault_sensor=args.fault_sensor,
        fault_mode=args.fault_mode,
        fault_value=args.fault_value,
        reuse_server=args.reuse_server,
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    latest = summary["status"]["data"]["latest_snapshot"]["measured_quality"]
    print(
        "HIL REST e2e complete:",
        f"simulation_id={summary['started']['data']['simulation_id']}",
        f"turbidity={latest['turbidity']}",
        f"do={latest['dissolved_oxygen']}",
        f"output={output_path}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
