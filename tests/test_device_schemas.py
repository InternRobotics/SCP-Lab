import asyncio
import json
from pathlib import Path

import pytest

from scp_lab.adapters.heater.backend import MockHeaterBackend
from scp_lab.adapters.offline import OfflineBackend
from scp_lab.conformance import check_runtime
from scp_lab.execution_models import (
    BackendResult,
    BackendState,
    DeviceDescriptor,
    DeviceState,
    ExecutionRecord,
    ExecutionRequest,
    ProtocolError,
    StateObservation,
)
from scp_lab.registry import create_runtime
from scp_lab.runtime import LocalExecutionRuntime


def request(**overrides):
    return ExecutionRequest(
        **{
            "device_id": "demo-heater",
            "capability_id": "demo_heater.hold",
            "arguments": {"target_celsius": 37, "duration_s": 0.01},
            **overrides,
        }
    )


def test_static_descriptor_is_independent_of_availability_and_occupancy():
    class SwitchableBackend(MockHeaterBackend):
        available = True

        def read_state(self):
            return BackendState(available=self.available)

    async def scenario():
        backend = SwitchableBackend()
        runtime = LocalExecutionRuntime([backend])
        descriptor = runtime.describe_device("demo-heater")
        assert "state" not in descriptor and "available" not in descriptor
        assert descriptor["state_schema"] is None
        assert descriptor["configuration_version"] is None
        backend.available = False
        assert runtime.device_state("demo-heater")["state"] == "unavailable"
        with pytest.raises(ProtocolError, match="Unavailable"):
            await runtime.submit(request())
        backend.available = True
        record = await runtime.submit(request())
        assert runtime.device_state("demo-heater")["state"] == "busy"
        assert runtime.describe_device("demo-heater") == descriptor
        await runtime.tasks[record["run_id"]]
        assert runtime.device_state("demo-heater")["state"] == "idle"
        assert runtime.describe_device("demo-heater") == descriptor
        assert record["descriptor_revision"] == descriptor["descriptor_revision"]

    asyncio.run(scenario())


def test_descriptor_revision_detects_schema_change_and_can_be_pinned():
    async def scenario():
        first = LocalExecutionRuntime([MockHeaterBackend()]).describe_device("demo-heater")
        backend = MockHeaterBackend()
        backend.capabilities[0].input_schema["properties"]["duration_s"]["maximum"] = 5
        runtime = LocalExecutionRuntime([backend])
        current = runtime.describe_device("demo-heater")
        assert first["descriptor_revision"] != current["descriptor_revision"]
        with pytest.raises(ProtocolError) as error:
            await runtime.submit(request(expected_descriptor_revision=first["descriptor_revision"]))
        assert error.value.error.code == "descriptor_changed"
        assert runtime.runs == {}
        record = await runtime.submit(
            request(expected_descriptor_revision=current["descriptor_revision"])
        )
        await runtime.tasks[record["run_id"]]

    asyncio.run(scenario())


def test_resolved_defaults_are_recorded_without_rewriting_original_request():
    async def scenario():
        runtime = LocalExecutionRuntime([MockHeaterBackend()])
        call = request(arguments={"target_celsius": 37}, idempotency_key="optional-duration")
        record = await runtime.submit(call)
        assert record["request"]["arguments"] == {"target_celsius": 37}
        assert record["effective_arguments"] == {"target_celsius": 37, "duration_s": 1}
        record["effective_arguments"]["duration_s"] = 10
        await runtime.cancel(record["run_id"])
        await runtime.tasks[record["run_id"]]
        final = runtime.get_execution(record["run_id"])
        assert final["effective_arguments"]["duration_s"] == 1
        assert final["updated_at"] >= final["submitted_at"]
        assert (await runtime.submit(call))["run_id"] == record["run_id"]

    asyncio.run(scenario())


def test_defaults_cannot_be_applied_without_declaring_the_policy():
    async def scenario():
        backend = MockHeaterBackend()
        backend.capabilities[0].defaults_policy = "not_applied"
        runtime = LocalExecutionRuntime([backend])
        with pytest.raises(ProtocolError) as error:
            await runtime.submit(request(arguments={"target_celsius": 37}))
        assert error.value.error.code == "invalid_backend_defaults"
        assert runtime.runs == {}

    asyncio.run(scenario())


def test_declared_observation_schema_and_original_observation_timestamp():
    class ObservedBackend(MockHeaterBackend):
        def read_state(self):
            return BackendState(
                observation=StateObservation(
                    values={"vendor_temperature": self.value},
                    observed_at="2026-10-08T00:00:00+00:00",
                    source="offline_fixture",
                    kind="simulated",
                )
            )

    backend = ObservedBackend()
    backend.value = 23.5
    backend.description.state_schema = {
        "type": "object",
        "properties": {"vendor_temperature": {"type": "number", "x-scp-unit": "degC"}},
        "required": ["vendor_temperature"],
        "additionalProperties": False,
    }
    runtime = LocalExecutionRuntime([backend])
    first, second = runtime.device_state("demo-heater"), runtime.device_state("demo-heater")
    assert first["observation"] == second["observation"]
    assert first["observation"]["observed_at"] != first["reported_at"]
    backend.value = "23.5 degC"
    with pytest.raises(ProtocolError) as error:
        runtime.device_state("demo-heater")
    assert error.value.error.code == "invalid_backend_state"


@pytest.mark.parametrize("released", [None, False, True])
def test_hardware_failure_does_not_implicitly_release_device(released):
    class HeldBackend(MockHeaterBackend):
        async def execute(self, request, context):
            # A software fixture; never connects to a physical device.
            return BackendResult(status="failed", device_released=released)

    async def scenario():
        backend = HeldBackend()
        backend.description.execution_mode = "hardware"
        backend.description.physical_execution = True
        runtime = LocalExecutionRuntime([backend])
        record = await runtime.submit(request())
        await runtime.tasks[record["run_id"]]
        final = runtime.get_execution(record["run_id"])
        assert final["status"] == "failed"
        assert final["device_released"] is (released is True)
        assert runtime.device_state("demo-heater")["state"] == (
            "idle" if released else "needs_attention"
        )

    asyncio.run(scenario())


def test_units_are_annotations_not_conversion_and_undeclared_units_stay_undeclared(device_models):
    backends = {d.definition.model_id: OfflineBackend(d) for d in device_models}
    ot2 = backends["ot2"]
    capability = next(c for c in ot2.capabilities if c.capability_id == "ot2.liquid_transfer")
    volume = capability.input_schema["properties"]["parameters"]["properties"]["volume"]
    assert volume["x-scp-unit"] == "uL"
    star = backends["hamilton_star"].capabilities[0]
    assert (
        star.input_schema["properties"]["parameters"]["properties"]["volume"]["x-scp-unit"] == "uL"
    )
    assert not star.limitations
    incubator = backends["cytomat_6002"]
    parameters = incubator.capabilities[0].input_schema["properties"]["parameters"]["properties"]
    assert parameters["duration"]["x-scp-unit"] == "min"
    assert parameters["temperature"]["x-scp-unit"] == "degC"
    shaker = backends["hamilton_heater_shaker"].capabilities[0]
    assert (
        "x-scp-unit" not in shaker.input_schema["properties"]["parameters"]["properties"]["speed"]
    )
    reader = backends["agilent_biotek_synergy_h1"].capabilities[0]
    assert (
        "x-scp-unit"
        not in reader.input_schema["properties"]["parameters"]["properties"]["focal_height"]
    )

    async def scenario():
        runtime = LocalExecutionRuntime([MockHeaterBackend(), incubator])
        with pytest.raises(ProtocolError):
            await runtime.submit(request(arguments={"target_celsius": "37 degC"}))
        with pytest.raises(ProtocolError):
            await runtime.submit(
                request(arguments={"target_celsius": {"value": 37, "unit": "degC"}})
            )
        record = await runtime.submit(request(arguments={"target_celsius": 37, "duration_s": 0.01}))
        assert record["effective_arguments"]["duration_s"] == 0.01
        await runtime.tasks[record["run_id"]]
        incubation = await runtime.submit(
            ExecutionRequest(
                device_id=incubator.description.device_id,
                capability_id=incubator.capabilities[0].capability_id,
                arguments={
                    "parameters": {"duration": 0.5, "temperature": 37},
                    "bindings": {"sample": {"resource_id": "plate"}},
                },
            )
        )
        await runtime.tasks[incubation["run_id"]]
        final = runtime.get_execution(incubation["run_id"])
        assert final["status"] == "succeeded"
        assert final["effective_arguments"]["parameters"]["duration"] == 0.5
        assert final["result"]["validated_command"]["parameters"]["duration"] == 0.5

    asyncio.run(scenario())


def test_required_fields_remain_required_even_when_schema_has_a_default(device_models):
    backend = OfflineBackend(
        next(d for d in device_models if d.definition.model_id == "agilent_centrifuge_773")
    )
    with pytest.raises(ProtocolError):
        backend.validate(
            ExecutionRequest(
                device_id=backend.description.device_id,
                capability_id=backend.capabilities[0].capability_id,
                arguments={
                    "parameters": {"speed": 1000, "duration": 30},
                    "bindings": {"sample": {"resource_id": "plate"}},
                },
            )
        )


def test_lightweight_checks_cover_all_registered_devices_without_execution():
    runtime = create_runtime()
    report = check_runtime(runtime)
    assert report["status"] == "passed"
    assert report["scope"] == "descriptor_and_state_schemas"
    assert report["execution_performed"] is False
    assert len(report["devices"]) == 48
    assert runtime.runs == {}
    assert runtime.list_devices()[0]["state"]["scope"] == "this_server_process"


def test_exported_device_and_execution_schemas_match_public_models():
    root = Path(__file__).resolve().parents[1] / "schemas"
    for name, model in (
        ("device-descriptor", DeviceDescriptor),
        ("device-state", DeviceState),
        ("execution-request", ExecutionRequest),
        ("execution-record", ExecutionRecord),
    ):
        assert json.loads((root / f"{name}.schema.json").read_text()) == model.model_json_schema()
