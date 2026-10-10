import os

import pytest
from test_protocol import EXAMPLES, load

from scp_lab.models import Protocol
from scp_lab.simulation import get_run, simulate_protocol


@pytest.mark.simulation
@pytest.mark.skipif(
    not os.environ.get("SCP_LAB_SIM_PYTHON"),
    reason="Set SCP_LAB_SIM_PYTHON for official simulation",
)
@pytest.mark.parametrize("path", sorted(EXAMPLES.glob("*.json")), ids=lambda p: p.stem)
def test_official_simulation(path, tmp_path, monkeypatch):
    monkeypatch.setenv("SCP_LAB_RUN_DIR", str(tmp_path))
    result = simulate_protocol(Protocol.model_validate_json(path.read_text()))
    assert result["status"] == "succeeded", result
    assert result["command_count"] > 0
    assert result["sdk_version"] == "8.8.2"
    assert result["completion_evidence"]["physical_completion_verified"] is False
    assert get_run(result["run_id"]) == result


def test_missing_simulator_is_not_success(tmp_path, monkeypatch):
    monkeypatch.delenv("SCP_LAB_SIM_PYTHON", raising=False)
    monkeypatch.setenv("SCP_LAB_RUN_DIR", str(tmp_path))
    monkeypatch.setattr("scp_lab.simulation.importlib.util.find_spec", lambda _: None)
    result = simulate_protocol(Protocol.model_validate(load()))
    assert result["status"] == "unavailable"
    assert result["completion_evidence"]["kind"] == "none"


def test_run_id_cannot_be_a_path():
    with pytest.raises(ValueError):
        get_run("../../anything")
