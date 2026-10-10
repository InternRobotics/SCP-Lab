import asyncio
import json
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from scp_lab.client_config import make_client_config
from scp_lab.device_config import DeviceConfig, load_device_configs
from scp_lab.execution_models import ExecutionRequest
from scp_lab.registry import create_runtime

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def clean_settings(monkeypatch):
    monkeypatch.delenv("SCP_LAB_DEVICES_DIR", raising=False)
    monkeypatch.delenv("SCP_LAB_BACKEND_FACTORY", raising=False)


def save(directory, filename="heater.json", **overrides):
    value = {
        "device_id": "heater-01",
        "backend": "scp_lab.adapters.heater.backend:create_backend",
        **overrides,
    }
    path = directory / filename
    path.write_text(json.dumps(value))
    return path


def test_bundled_instances_use_the_same_configuration_loader(device_models):
    configs = [config for _, config in load_device_configs()]
    assert len(configs) == 48
    models = {c.options["model_resource"] for c in configs if "model_resource" in c.options}
    assert models == {d.source["model_resource"] for d in device_models}
    runtime = create_runtime()
    assert {c.device_id for c in configs} == set(runtime.backends)
    assert sum(len(d.capabilities) for d in runtime.descriptors.values()) == 100
    schema = json.loads((ROOT / "schemas/device-config.schema.json").read_text())
    assert schema == DeviceConfig.model_json_schema()
    for config in configs:
        Draft202012Validator(schema).validate(config.model_dump())


def test_explicit_directory_replaces_demos_and_overrides_environment(tmp_path, monkeypatch):
    other = tmp_path / "other"
    other.mkdir()
    save(tmp_path)
    monkeypatch.setenv("SCP_LAB_DEVICES_DIR", str(tmp_path))
    assert set(create_runtime().backends) == {"heater-01"}
    assert create_runtime(other).backends == {}
    with pytest.raises(ValueError, match="does not exist"):
        create_runtime(tmp_path / "missing")
    monkeypatch.setenv("SCP_LAB_DEVICES_DIR", "")
    with pytest.raises(ValueError, match="must not be empty"):
        create_runtime()


def test_files_persist_and_changes_apply_only_on_restart(tmp_path):
    first_file = save(tmp_path, display_name="First heater")
    second_file = save(tmp_path, "second.json", device_id="heater-02")
    original = second_file.read_bytes()
    current = create_runtime(tmp_path)
    assert current.describe_device("heater-01")["display_name"] == "First heater"
    assert set(current.backends) == {"heater-01", "heater-02"}
    value = json.loads(first_file.read_text())
    value["enabled"] = False
    first_file.write_text(json.dumps(value))
    assert set(current.backends) == {"heater-01", "heater-02"}
    assert set(create_runtime(tmp_path).backends) == {"heater-02"}
    assert second_file.read_bytes() == original
    assert first_file.exists()


def test_two_instances_share_adapter_but_not_sdk_or_observations(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "examples/adapters"))
    runtime = create_runtime(ROOT / "examples/devices")
    first, second = runtime.backends["reader-01"], runtime.backends["reader-02"]
    assert type(first) is type(second)
    assert first.sdk is not second.sdk

    async def scenario():
        record = await runtime.submit(
            ExecutionRequest(
                device_id="reader-01",
                capability_id="example_reader.read_absorbance",
                arguments={"plate_id": "plate-a", "wavelength_nm": 600},
            )
        )
        await runtime.tasks[record["run_id"]]
        result = runtime.get_execution(record["run_id"])
        assert result["status"] == "succeeded"
        assert result["result"]["values"]["A1"] == 0.123
        assert first.read_state().observation.values == {"last_plate_id": "plate-a"}
        assert second.read_state().observation is None
        await runtime.aclose()

    asyncio.run(scenario())


def test_duplicate_ids_rejected_before_constructing_backends(tmp_path, monkeypatch):
    import scp_lab.adapters.heater.backend as backends

    def unexpected(_config):
        pytest.fail("A backend was constructed before duplicate validation")

    monkeypatch.setattr(backends, "create_backend", unexpected)
    save(tmp_path)
    save(tmp_path, "disabled.json", enabled=False)
    with pytest.raises(ValueError, match="Duplicate device_id"):
        create_runtime(tmp_path)


def test_disabled_device_does_not_import_or_construct_backend(tmp_path):
    save(tmp_path, enabled=False, backend="absent_adapter:create_backend")
    assert create_runtime(tmp_path).backends == {}


@pytest.mark.parametrize(
    "overrides,match",
    [
        ({"enabled": "false"}, "enabled"),
        ({"backend": "not-a-factory"}, "backend"),
        ({"device_id": ""}, "device_id"),
        ({"physical_execution": True}, "physical_execution"),
        ({"options": {"typo": True}}, "typo"),
        ({"connection": {"host": "localhost"}}, "host"),
        ({"backend": "absent_adapter:create_backend"}, "absent_adapter"),
        (
            {
                "backend": "scp_lab.adapters.offline:create_backend",
                "options": {"model_resource": "scp_lab.adapters.plate_reader:models/absent.json"},
            },
            "Cannot load model",
        ),
    ],
)
def test_invalid_configuration_is_actionable(tmp_path, overrides, match):
    save(tmp_path, **overrides)
    with pytest.raises(ValueError, match=match) as error:
        create_runtime(tmp_path)
    assert "heater.json" in str(error.value)


@pytest.mark.parametrize(
    "text",
    [
        '{"device_id":"one","device_id":"two","backend":"m:f"}',
        '{"device_id":"one","backend":"m:f","options":{"x":NaN}}',
        '{"device_id":',
    ],
)
def test_ambiguous_or_invalid_json_is_rejected(tmp_path, text):
    (tmp_path / "bad.json").write_text(text)
    with pytest.raises(ValueError, match="bad.json"):
        create_runtime(tmp_path)


def test_adapter_cannot_return_an_unrelated_instance(tmp_path, monkeypatch):
    from scp_lab.adapters.heater import backend as backends

    save(tmp_path)
    monkeypatch.setattr(backends, "create_backend", lambda _: backends.MockHeaterBackend())
    with pytest.raises(ValueError, match="must match"):
        create_runtime(tmp_path)


def test_old_factory_setting_has_migration_error(tmp_path, monkeypatch):
    monkeypatch.setenv("SCP_LAB_BACKEND_FACTORY", "old:create_backends")
    with pytest.raises(ValueError, match="per-device JSON"):
        create_runtime(tmp_path)


@pytest.mark.mcp
def test_saved_directory_survives_real_server_restart_outside_repo(tmp_path, monkeypatch):
    pytest.importorskip("mcp")
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    device_dir = tmp_path / "devices"
    device_dir.mkdir()
    device_file = save(device_dir)
    monkeypatch.chdir(tmp_path)
    config = make_client_config(ROOT, devices_dir=Path("devices"))["mcpServers"]["scp-lab"]
    assert config["env"]["SCP_LAB_DEVICES_DIR"] == str(device_dir)
    config["cwd"] = str(tmp_path)
    # As with a client configuration saved to disk, no parent-shell variable is required.
    assert config["command"] == sys.executable
    saved = tmp_path / "mcp.json"
    saved.write_text(json.dumps(config))

    async def discover():
        async with stdio_client(StdioServerParameters(**json.loads(saved.read_text()))) as (
            read,
            write,
        ):
            async with ClientSession(read, write) as client:
                await client.initialize()
                result = await client.call_tool("list_devices", {})
                assert not result.isError
                return {device["device_id"] for device in result.structuredContent["data"]}

    assert asyncio.run(discover()) == {"heater-01"}
    assert asyncio.run(discover()) == {"heater-01"}
    updated = json.loads(device_file.read_text())
    updated["enabled"] = False
    device_file.write_text(json.dumps(updated))
    assert asyncio.run(discover()) == set()
