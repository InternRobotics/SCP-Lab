import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.mcp
@pytest.mark.parametrize(
    "example",
    [
        "quickstart.py",
        "ot2_simulation.py",
        "01_device_call.py",
        "02_multi_device.py",
        "03_runtime.py",
        "04_custom_backend.py",
    ],
)
def test_examples_through_real_mcp_session(example, tmp_path):
    pytest.importorskip("mcp")
    if example == "ot2_simulation.py" and not os.environ.get("SCP_LAB_SIM_PYTHON"):
        pytest.skip("OT-2 example requires the optional simulator environment")
    arguments = [sys.executable, str(ROOT / "examples" / example)]
    if example == "01_device_call.py" and os.environ.get("SCP_LAB_SIM_PYTHON"):
        arguments.append("--simulate")
    result = subprocess.run(
        arguments,
        cwd=tmp_path,
        env={**os.environ, "SCP_LAB_RUN_DIR": str(tmp_path / "runs")},
        text=True,
        capture_output=True,
        timeout=90,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Processing request of type" not in result.stderr
    if example == "quickstart.py":
        lines = result.stdout.splitlines()
        assert "list_devices -> demo-heater (mock)" in lines
        assert "describe_device -> demo_heater.hold" in lines
        statuses = [line for line in lines if line.startswith("get_execution -> ")]
        assert statuses[-1] == "get_execution -> succeeded"
        assert all(previous != current for previous, current in zip(statuses, statuses[1:]))
        payload, _ = json.JSONDecoder().raw_decode(result.stdout.split("Result:\n", 1)[1])
        assert payload["status"] == "succeeded"
        assert payload["execution_mode"] == "mock"
        assert payload["physical_execution"] is False
        assert payload["result"]["requested_target_celsius"] == 37
        assert payload["result"]["measured_temperature"] is None
        assert lines[-1] == "get_device_state -> idle"
