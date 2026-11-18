"""Run a single, device-specific acquisition through SCP-Lab."""

import asyncio
from collections.abc import Callable

from scp_lab.adapters.schemas import load_model
from scp_lab.backend import DeviceBackend, ExecutionContext
from scp_lab.device_config import DeviceConfig
from scp_lab.execution_models import (
    BackendResult,
    CompletionEvidence,
    DeviceDescription,
    ExecutionError,
    ExecutionRequest,
)


class MeasurementBackend(DeviceBackend):
    def __init__(self, config: DeviceConfig, model: str, read: Callable[[], dict]):
        definition = load_model(model_resource=f"{__package__}:models/{model}.json").definition
        self.capabilities = definition.capabilities
        self.read = read
        self.description = DeviceDescription(
            device_id=config.device_id,
            model_id=definition.model_id,
            device_class=definition.device_class,
            display_name=definition.display_name,
            backend_id=f"example.{model}",
            execution_mode="hardware",
            physical_execution=True,
        )

    async def execute(self, request: ExecutionRequest, context: ExecutionContext) -> BackendResult:
        try:
            result = await asyncio.to_thread(self.read)
        except Exception as error:
            # These calls acquire a reading without changing any actuator state.
            return BackendResult(
                status="failed",
                error=ExecutionError(code="acquisition_failed", message=str(error)),
                device_released=True,
            )
        return BackendResult(
            result=result,
            completion_evidence=CompletionEvidence(
                kind="device_reported", details={"source": self.description.model_id}
            ),
            device_released=True,
        )
