import asyncio
import json
from pathlib import Path

import pytest

from scp_lab.adapters.heater.backend import MockHeaterBackend
from scp_lab.adapters.offline import OfflineBackend
from scp_lab.execution_models import (
    BackendResult,
    CompletionEvidence,
    ExecutionRequest,
    ProtocolError,
)
from scp_lab.registry import create_runtime
from scp_lab.runtime import LocalExecutionRuntime

ROOT = Path(__file__).resolve().parents[1]


def request(device_id="demo-heater", **overrides):
    return ExecutionRequest.model_validate(
        {
            "device_id": device_id,
            "capability_id": "demo_heater.hold",
            "arguments": {"target_celsius": 37, "duration_s": 0.02},
            **overrides,
        }
    )


async def finished(runtime, record):
    await runtime.tasks[record["run_id"]]
    return runtime.get_execution(record["run_id"])


def test_catalog_models_actions_and_all_class_examples(device_models):
    definitions = device_models
    assert len(definitions) == 45
    assert len({d.definition.device_class for d in definitions}) == 13
    assert sum(len(d.definition.capabilities) for d in definitions) == 89
    runtime = LocalExecutionRuntime([OfflineBackend(d) for d in definitions])
    requests = json.loads((ROOT / "examples/requests/device_classes.json").read_text())
    assert len({runtime.backends[r["device_id"]].description.device_class for r in requests}) == 13

    async def scenario():
        for value in requests:
            result = await finished(
                runtime, await runtime.submit(ExecutionRequest.model_validate(value))
            )
            assert result["status"] == "succeeded"
            assert result["execution_mode"] == "schema_validation"
            assert result["backend_id"] == "scp_lab.schema_validation.v1"
            assert result["completion_evidence"]["kind"] == "schema_validation"
            assert result["physical_execution"] is False
            assert "readings" not in result["result"]

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "device_id,parameters",
    [
        ("agilent_biotek_synergy_h1", {"mode": "fluorescence", "excitation_wavelength": 485}),
        (
            "agilent_centrifuge_773",
            {
                "speed": 5000,
                "duration": 30,
                "acceleration_percent": 100,
                "deceleration_percent": 100,
            },
        ),
        ("fluent_glovebox_2035", {"method_name": "test", "timeout": 10, "humidity": 10}),
        ("hamilton_tilt_module", {"angle": 10, "unknown_parameter": 42}),
    ],
)
def test_device_specific_constraints_reject_invalid_calls(device_id, parameters, device_models):
    device = next(d for d in device_models if d.definition.model_id == device_id)
    backend = OfflineBackend(device)
    call = ExecutionRequest(
        device_id=backend.description.device_id,
        capability_id=backend.capabilities[0].capability_id,
        arguments={"parameters": parameters, "bindings": {"sample": {"resource_id": "plate"}}},
    )
    with pytest.raises(ProtocolError) as error:
        backend.validate(call)
    assert error.value.error.code == "invalid_arguments"


def test_missing_binding_and_nonfinite_values_are_rejected(device_models):
    backend = OfflineBackend(
        next(d for d in device_models if d.definition.model_id == "hamilton_tilt_module")
    )
    call = ExecutionRequest(
        device_id=backend.description.device_id,
        capability_id=backend.capabilities[0].capability_id,
        arguments={"parameters": {"angle": 10}, "bindings": {}},
    )
    with pytest.raises(ProtocolError):
        backend.validate(call)
    with pytest.raises(ValueError):
        request(arguments={"duration_s": float("nan"), "target_celsius": 37})


def test_busy_idempotency_cancellation_and_reuse():
    async def scenario():
        runtime = LocalExecutionRuntime([MockHeaterBackend()])
        call = request(idempotency_key="stable", arguments={"target_celsius": 37, "duration_s": 1})
        first, duplicate = await asyncio.gather(runtime.submit(call), runtime.submit(call))
        assert first["run_id"] == duplicate["run_id"]
        assert runtime.device_state("demo-heater")["state"] == "busy"
        with pytest.raises(ProtocolError) as error:
            await runtime.submit(request(idempotency_key="other"))
        assert error.value.error.code == "device_busy"
        with pytest.raises(ProtocolError) as error:
            await runtime.submit(request(idempotency_key="stable"))
        assert error.value.error.code == "idempotency_conflict"
        cancelled = await runtime.cancel(first["run_id"])
        assert cancelled["status"] == "cancel_requested"
        result = await finished(runtime, first)
        assert result["status"] == "cancelled"
        assert runtime.device_state("demo-heater")["state"] == "idle"
        assert (await finished(runtime, await runtime.submit(request())))["status"] == "succeeded"
        assert (await runtime.submit(call))["run_id"] == first["run_id"]
        await runtime.aclose()

    asyncio.run(scenario())


def test_submission_and_read_snapshots_cannot_mutate_live_request():
    async def scenario():
        runtime = LocalExecutionRuntime([MockHeaterBackend()])
        call = request()
        record = await runtime.submit(call)
        call.arguments["target_celsius"] = 90
        record["request"]["arguments"]["target_celsius"] = 80
        result = await finished(runtime, record)
        assert result["result"]["requested_target_celsius"] == 37

    asyncio.run(scenario())


def test_parallel_devices_and_failures_release_confirmed_runs():
    async def scenario():
        runtime = LocalExecutionRuntime(
            [MockHeaterBackend(), MockHeaterBackend("fault", fail=True)]
        )
        first, second = await asyncio.gather(
            runtime.submit(request()), runtime.submit(request("fault"))
        )
        success, failure = await asyncio.gather(finished(runtime, first), finished(runtime, second))
        assert success["status"] == "succeeded"
        assert failure["status"] == "failed"
        assert failure["error"]["code"] == "demo_heater_fault"
        assert runtime.device_state("fault")["state"] == "idle"

    asyncio.run(scenario())


def test_uncertain_hardware_exception_keeps_device_reserved():
    class DisconnectedBackend(MockHeaterBackend):
        async def execute(self, request, context):
            raise ConnectionError("Test transport disconnected; no real hardware used")

    async def scenario():
        backend = DisconnectedBackend()
        backend.description.execution_mode = "hardware"
        backend.description.physical_execution = True
        runtime = LocalExecutionRuntime([backend])
        outcome = await finished(runtime, await runtime.submit(request()))
        assert outcome["status"] == "unknown"
        assert not outcome["completion_evidence"]["physical_completion_verified"]
        assert runtime.device_state("demo-heater")["state"] == "needs_attention"
        with pytest.raises(ProtocolError) as error:
            await runtime.submit(request())
        assert error.value.error.code == "device_busy"

    asyncio.run(scenario())


def test_nonhardware_backend_cannot_claim_physical_completion():
    class IncorrectBackend(MockHeaterBackend):
        async def execute(self, request, context):
            return BackendResult(
                result={
                    "requested_target_celsius": 37,
                    "elapsed_demo_seconds": 0.02,
                    "measured_temperature": None,
                },
                completion_evidence=CompletionEvidence(
                    kind="mock_trace", physical_completion_verified=True
                ),
            )

    async def scenario():
        runtime = LocalExecutionRuntime([IncorrectBackend()])
        result = await finished(runtime, await runtime.submit(request()))
        assert result["status"] == "failed"
        assert "Non-hardware backends" in result["error"]["message"]
        assert not result["completion_evidence"]["physical_completion_verified"]

    asyncio.run(scenario())


def test_invalid_backend_result_is_not_reported_as_success():
    class InvalidResultBackend(MockHeaterBackend):
        async def execute(self, request, context):
            return BackendResult(
                result={"unexpected": "value"},
                completion_evidence=CompletionEvidence(kind="mock_trace"),
            )

    async def scenario():
        runtime = LocalExecutionRuntime([InvalidResultBackend()])
        result = await finished(runtime, await runtime.submit(request()))
        assert result["status"] == "failed"
        assert result["error"]["details"]["exception_type"] == "ValidationError"

    asyncio.run(scenario())


def test_cancellation_not_advertised_is_not_forced():
    async def scenario():
        backend = MockHeaterBackend()
        backend.description.cancellation_supported = False
        runtime = LocalExecutionRuntime([backend])
        record = await runtime.submit(request())
        with pytest.raises(ProtocolError) as error:
            await runtime.cancel(record["run_id"])
        assert error.value.error.code == "cancellation_unsupported"
        assert (await finished(runtime, record))["status"] == "succeeded"

    asyncio.run(scenario())


def test_plugin_factory_and_duplicate_instance_rejection(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "examples"))
    runtime = create_runtime(ROOT / "examples" / "devices")
    assert set(runtime.backends) == {"reader-01", "reader-02"}
    assert runtime.describe_device("reader-01")["execution_mode"] == "mock"
    with pytest.raises(ValueError, match="Duplicate device instance"):
        LocalExecutionRuntime([MockHeaterBackend(), MockHeaterBackend()])
