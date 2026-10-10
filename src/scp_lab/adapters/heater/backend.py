"""Timed heater demonstration with progress, cancellation, and injected failure."""

from pydantic import StrictBool

from scp_lab.backend import DeviceBackend, ExecutionContext
from scp_lab.device_config import DeviceConfig
from scp_lab.execution_models import (
    BackendResult,
    CompletionEvidence,
    Contract,
    DeviceDescription,
    ExecutionError,
    ExecutionRequest,
)

from .schemas import get_capabilities


class MockHeaterBackend(DeviceBackend):
    """A timed state-machine example; no thermodynamics or measured temperature is simulated."""

    def __init__(self, device_id="demo-heater", *, fail=False):
        self.fail = fail
        self.description = DeviceDescription(
            device_id=device_id,
            model_id="demo_heater",
            device_class="temperature_controller",
            display_name="Mock heater (injected failure)" if fail else "Mock heater",
            backend_id="scp_lab.mock_heater.v1",
            execution_mode="mock",
            cancellation_supported=True,
            provider="SCP-Lab reference implementation",
        )
        self.capabilities = get_capabilities()

    def resolve_arguments(self, request: ExecutionRequest) -> dict:
        arguments = super().resolve_arguments(request)
        arguments.setdefault("duration_s", 1)
        return arguments

    async def execute(self, request: ExecutionRequest, context: ExecutionContext) -> BackendResult:
        duration = request.arguments["duration_s"]
        for step in range(10):
            if await context.wait(duration / 10):
                return BackendResult(
                    status="cancelled",
                    completion_evidence=CompletionEvidence(
                        kind="mock_trace",
                        details={"event": "mock timer stopped"},
                    ),
                )
            context.report_progress({"fraction": (step + 1) / 10, "stage": "mock_hold"})
        if self.fail:
            return BackendResult(
                status="failed",
                error=ExecutionError(code="demo_heater_fault", message="Injected mock failure"),
                completion_evidence=CompletionEvidence(kind="mock_trace"),
            )
        return BackendResult(
            result={
                "requested_target_celsius": request.arguments["target_celsius"],
                "elapsed_demo_seconds": duration,
                "measured_temperature": None,
            },
            completion_evidence=CompletionEvidence(kind="mock_trace"),
        )


class HeaterOptions(Contract):
    fail: StrictBool = False


def create_backend(config: DeviceConfig) -> DeviceBackend:
    Contract.model_validate(config.connection)
    options = HeaterOptions.model_validate(config.options)
    return MockHeaterBackend(device_id=config.device_id, fail=options.fail)
