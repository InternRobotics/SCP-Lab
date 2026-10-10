"""Optional official simulation, isolated from MCP stdout and core dependencies."""

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from .compiler import compile_protocol
from .models import Protocol


def now():
    return datetime.now(timezone.utc).isoformat()


def run_directory() -> Path:
    return Path(os.environ.get("SCP_LAB_RUN_DIR", ".scp-lab/runs"))


def simulate_protocol(protocol: Protocol) -> dict:
    compiled = compile_protocol(protocol)
    canonical = protocol.model_dump_json()
    record = {
        "schema_version": "scp-lab.simulation-run.v0.1",
        "run_id": str(uuid4()),
        "experiment_id": protocol.experiment_id,
        "started_at": now(),
        "execution_mode": "official_simulation",
        "physical_execution": False,
        "protocol_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
        "code_sha256": hashlib.sha256(compiled["code"].encode()).hexdigest(),
        "protocol": protocol.model_dump(),
        "generated_code": compiled["code"],
        "validation": compiled["validation"],
        "completion_evidence": {"kind": "none", "physical_completion_verified": False},
    }
    simulator_python = os.environ.get("SCP_LAB_SIM_PYTHON")
    if not simulator_python and importlib.util.find_spec("opentrons") is None:
        result = {
            "status": "unavailable",
            "error": "Install requirements-simulation.txt in a separate environment and set SCP_LAB_SIM_PYTHON to its Python executable. No simulation was performed.",
        }
    else:
        with tempfile.TemporaryDirectory(prefix="scp-lab-") as directory:
            source = Path(directory) / "protocol.py"
            source.write_text(compiled["code"], encoding="utf-8")
            # Keep each simulator's configuration local, independent of user robot settings.
            child_env = {
                k: v
                for k, v in os.environ.items()
                if not k.startswith("OT_API_") and k not in ("RUNNING_ON_PI", "RUNNING_ON_VERDIN")
            }
            child_env["OT_API_CONFIG_DIR"] = str(Path(directory) / "opentrons-config")
            try:
                child = subprocess.run(
                    [
                        simulator_python or sys.executable,
                        str(Path(__file__).with_name("sim_worker.py")),
                        str(source),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    check=False,
                    env=child_env,
                )
                if child.returncode:
                    result = {
                        "status": "failed",
                        "error": child.stderr[-20000:] or "Simulation process failed",
                    }
                else:
                    result = json.loads(child.stdout)
                    if child.stderr:
                        result["process_diagnostics"] = child.stderr[-20000:]
            except subprocess.TimeoutExpired:
                result = {
                    "status": "failed",
                    "error_type": "SimulationTimeout",
                    "error": "Official simulation exceeded 60 seconds.",
                }
            except (OSError, json.JSONDecodeError) as error:
                result = {
                    "status": "failed",
                    "error_type": type(error).__name__,
                    "error": str(error),
                }
    record.update(result)
    record["finished_at"] = now()
    if record["status"] == "succeeded":
        record["completion_evidence"]["kind"] = "official_simulator_runlog"
    directory = run_directory()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (record["run_id"] + ".json")
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)
    return record


def get_run(run_id: str) -> dict:
    normalized = str(UUID(run_id))
    return json.loads((run_directory() / (normalized + ".json")).read_text(encoding="utf-8"))
