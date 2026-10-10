import asyncio
import json
import sys
from copy import deepcopy
from pathlib import Path

import pytest

from scp_lab.adapters.offline import OfflineBackend
from scp_lab.adapters.schemas import DeviceModel, load_model
from scp_lab.device_config import load_device_configs
from scp_lab.execution_models import ExecutionRequest, ProtocolError
from scp_lab.registry import create_runtime

ROOT = Path(__file__).resolve().parents[1]
TILTER = "scp_lab.adapters.tilter:models/hamilton_tilt_module.json"


def test_every_shipped_definition_is_independent_and_used(device_models):
    files = set((ROOT / "src/scp_lab/adapters").glob("*/models/*.json"))
    assert len(files) == 46  # 45 offline models and the demonstration heater.
    expected = {
        ROOT / "src" / m.source["model_resource"].replace(".", "/", 2).replace(":", "/")
        for m in device_models
    }
    assert expected | {ROOT / "src/scp_lab/adapters/heater/models/demo_heater.json"} == files
    for path in files:
        definition = load_model(model_file=path).definition
        assert definition.model_id == path.stem
    exported = json.loads((ROOT / "schemas/device-model.schema.json").read_text())
    assert exported == DeviceModel.model_json_schema()


def test_loading_a_model_does_not_scan_others(tmp_path, monkeypatch):
    package = tmp_path / "independent_adapter"
    (package / "models").mkdir(parents=True)
    (package / "__init__.py").write_text("")
    source = load_model(model_resource=TILTER).definition.model_dump()
    (package / "models/selected.json").write_text(json.dumps(source))
    (package / "models/unrelated.json").write_text("broken unrelated definition")
    monkeypatch.syspath_prepend(str(tmp_path))
    selected = load_model(model_resource="independent_adapter:models/selected.json")
    assert selected.definition.model_id == source["model_id"]
    with pytest.raises(ValueError, match="unrelated.json"):
        load_model(model_resource="independent_adapter:models/unrelated.json")


def test_two_instances_own_separate_capability_objects():
    model = load_model(model_resource=TILTER)
    first = OfflineBackend(model, device_id="one")
    second = OfflineBackend(model, device_id="two")
    first.capabilities[0].input_schema.clear()
    assert second.capabilities[0].input_schema
    assert model.definition.capabilities[0].input_schema


def local_model_and_instances(tmp_path):
    definition = load_model(model_resource=TILTER).definition.model_dump()
    definition["model_id"] = "local_tilter"
    definition["device_class"] = "user_defined_class"
    definition["capabilities"][0]["capability_id"] = "local_tilter.tilt"
    model_file = tmp_path / "local_tilter.json"
    model_file.write_text(json.dumps(definition))
    devices = tmp_path / "devices"
    devices.mkdir()
    for device_id in ("tilter-01", "tilter-02"):
        (devices / f"{device_id}.json").write_text(
            json.dumps(
                {
                    "device_id": device_id,
                    "backend": "scp_lab.adapters.offline:create_backend",
                    "options": {"model_file": str(model_file)},
                }
            )
        )
    return model_file, devices, definition


def test_new_model_needs_no_catalog_registration_and_updates_on_restart(tmp_path):
    model_file, devices, definition = local_model_and_instances(tmp_path)
    running = create_runtime(devices)
    before = running.describe_device("tilter-01")
    assert before["device_class"] == "user_defined_class"
    updated = deepcopy(definition)
    updated["capabilities"][0]["input_schema"]["properties"]["parameters"]["properties"]["angle"][
        "maximum"
    ] = 5
    model_file.write_text(json.dumps(updated))
    assert running.describe_device("tilter-01") == before
    restarted = create_runtime(devices)
    assert (
        restarted.describe_device("tilter-01")["descriptor_revision"]
        != before["descriptor_revision"]
    )
    call = ExecutionRequest(
        device_id="tilter-01",
        capability_id="local_tilter.tilt",
        arguments={"parameters": {"angle": 10}, "bindings": {"sample": {"resource_id": "plate"}}},
    )
    running.backends["tilter-01"].validate(call)
    with pytest.raises(ProtocolError):
        restarted.backends["tilter-01"].validate(call)


@pytest.mark.mcp
def test_external_model_only_integration_through_real_mcp(tmp_path):
    pytest.importorskip("mcp")
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    model_file, devices, _ = local_model_and_instances(tmp_path)
    original = model_file.read_bytes()

    async def scenario():
        parameters = StdioServerParameters(
            command=sys.executable,
            args=["-m", "scp_lab.server"],
            env={"SCP_LAB_DEVICES_DIR": str(devices)},
            cwd=str(tmp_path),
        )
        async with stdio_client(parameters) as (read, write):
            async with ClientSession(read, write) as client:
                await client.initialize()
                discovered = await client.call_tool("list_devices", {})
                assert {d["device_id"] for d in discovered.structuredContent["data"]} == {
                    "tilter-01",
                    "tilter-02",
                }
                for device_id in ("tilter-01", "tilter-02"):
                    response = await client.call_tool(
                        "submit_execution",
                        {
                            "request": {
                                "device_id": device_id,
                                "capability_id": "local_tilter.tilt",
                                "arguments": {
                                    "parameters": {"angle": 10},
                                    "bindings": {"sample": {"resource_id": "plate"}},
                                },
                            }
                        },
                    )
                    assert not response.isError
                    run_id = response.structuredContent["data"]["run_id"]
                    for _ in range(100):
                        response = await client.call_tool("get_execution", {"run_id": run_id})
                        record = response.structuredContent["data"]
                        if record["status"] == "succeeded":
                            break
                        await asyncio.sleep(0.01)
                    assert record["status"] == "succeeded"
                    assert record["result"]["source"]["model_file"] == str(model_file)
                    assert record["completion_evidence"]["kind"] == "schema_validation"

    asyncio.run(scenario())
    assert model_file.read_bytes() == original
    assert len(load_device_configs(devices)) == 2


@pytest.mark.parametrize(
    "options",
    [
        {},
        {"model_file": "relative.json"},
        {"model_resource": TILTER, "model_file": "/unused.json"},
        {"model_resource": "scp_lab.adapters.tilter:../other.json"},
        {"model_resource": "scp_lab.adapters.tilter:/other.json"},
        {"model_resource": "not-a-package:models/x.json"},
    ],
)
def test_invalid_model_sources_are_rejected(options):
    with pytest.raises(ValueError):
        load_model(**options)


@pytest.mark.parametrize(
    "mutation", ["duplicate_key", "duplicate_capability", "nan", "unknown_field", "invalid_schema"]
)
def test_malformed_model_definitions_are_rejected_with_file_context(tmp_path, mutation):
    definition = load_model(model_resource=TILTER).definition.model_dump()
    if mutation == "duplicate_capability":
        definition["capabilities"] *= 2
    if mutation == "nan":
        definition["capabilities"][0]["input_schema"]["default"] = float("nan")
    if mutation == "unknown_field":
        definition["connection"] = {}
    if mutation == "invalid_schema":
        definition["capabilities"][0]["input_schema"] = {"type": "not_a_json_type"}
    text = json.dumps(definition)
    if mutation == "duplicate_key":
        text = text.replace('"model_id":', '"model_id":"duplicate", "model_id":', 1)
    path = tmp_path / "broken.json"
    path.write_text(text)
    with pytest.raises(ValueError, match="broken.json"):
        load_model(model_file=path)
