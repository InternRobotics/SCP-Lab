import ast
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from scp_lab.compiler import compile_protocol
from scp_lab.models import Protocol
from scp_lab.validation import validate

EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "protocols"


def load(name="serial_dilution"):
    return json.loads((EXAMPLES / (name + ".json")).read_text())


@pytest.mark.parametrize("path", sorted(EXAMPLES.glob("*.json")), ids=lambda p: p.stem)
def test_examples_compile(path):
    result = compile_protocol(Protocol.model_validate_json(path.read_text()))
    ast.parse(result["code"])
    assert result["validation"]["physical_execution"] is False


def test_nominal_volume_and_ancestry():
    result = validate(Protocol.model_validate(load()))
    wells = {w["location"]: w for w in result["predicted_wells"]}
    assert result["required_tips"] == 9
    assert wells["plate/A4"]["volume_ul"] == 200
    assert wells["plate/A4"]["source_sample_ids"] == ["diluent", "dye"]
    assert sum(w["volume_ul"] for w in wells.values()) == 1200


@pytest.mark.parametrize(
    "mutation,match",
    [
        (lambda d: d["setup"]["labware"][1].update(location="1"), "conflict"),
        (lambda d: d["steps"][0].update(volume_per_destination_ul=301), "pipette range"),
        (lambda d: d["liquids"][0].update(volume_ul=100), "insufficient"),
        (lambda d: d["steps"][1]["destination"].update(labware="missing"), "Unknown labware"),
        (
            lambda d: d["steps"][1]["source"].update(labware="reservoir", well="B1"),
            "Invalid liquid well",
        ),
        (lambda d: d["setup"]["pipette"].update(tip_racks=["plate"]), "does not match"),
        (lambda d: d["setup"]["pipette"].update(tip_racks=["tips", "tips"]), "Duplicate"),
        (lambda d: d["steps"][1].update(id="add_diluent"), "Step IDs"),
        (lambda d: d["liquids"].append(d["liquids"][0].copy()), "Duplicate initial"),
    ],
)
def test_reject_invalid_requests(mutation, match):
    data = load()
    mutation(data)
    with pytest.raises(ValueError, match=match):
        validate(Protocol.model_validate(data))


def test_overflow():
    data = load()
    data["liquids"].append(
        {"sample_id": "existing", "location": {"labware": "plate", "well": "A2"}, "volume_ul": 150}
    )
    with pytest.raises(ValueError, match="overflow"):
        validate(Protocol.model_validate(data))


def test_tip_exhaustion():
    data = load("pooling")
    data["steps"] = [
        {
            "id": f"mix_{i}",
            "action": "pipette_mixing",
            "sample": {"labware": "plate", "well": "A1"},
            "volume_ul": 50,
            "repetitions": 1,
        }
        for i in range(97)
    ]
    with pytest.raises(ValueError, match="fresh tips"):
        validate(Protocol.model_validate(data))


def test_module_must_be_present():
    data = load("temperature_hold")
    data["setup"]["modules"] = []
    with pytest.raises(ValueError, match="Unknown location"):
        validate(Protocol.model_validate(data))


@pytest.mark.parametrize("volume", [-1, 0, float("inf"), float("nan"), True, "100"])
def test_strict_numeric_inputs(volume):
    data = load()
    data["steps"][1]["volume_ul"] = volume
    with pytest.raises(ValidationError):
        Protocol.model_validate(data)


def test_unsupported_action_and_fields():
    data = load()
    data["steps"][1]["action"] = "transfer_with_liquid_class"
    with pytest.raises(ValidationError):
        Protocol.model_validate(data)
    data = load()
    data["steps"][1]["volume_ml"] = 1
    with pytest.raises(ValidationError):
        Protocol.model_validate(data)


def test_schema_files_match_models():
    from scp_lab.capabilities import list_capabilities, protocol_schema

    root = EXAMPLES.parents[1] / "schemas"
    assert json.loads((root / "protocol.schema.json").read_text()) == protocol_schema()
    assert json.loads((root / "ot2-capabilities.json").read_text()) == list_capabilities()
