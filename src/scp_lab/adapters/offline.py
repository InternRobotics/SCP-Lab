"""Shared offline backend for independently stored capability definitions."""

from scp_lab.backend import DeviceBackend, ExecutionContext
from scp_lab.device_config import DeviceConfig
from scp_lab.execution_models import (
    BackendResult,
    CompletionEvidence,
    Contract,
    DeviceDescription,
    ExecutionRequest,
)

from .schemas import LoadedModel, load_model


class OfflineBackend(DeviceBackend):
    def __init__(self, model: LoadedModel, *, device_id: str | None = None):
        # Each instance owns its definitions; changing one instance cannot change another.
        definition = model.definition.model_copy(deep=True)
        self.source = dict(model.source)
        self.description = DeviceDescription(
            device_id=device_id if device_id is not None else f"{definition.model_id}-validation",
            model_id=definition.model_id,
            device_class=definition.device_class,
            display_name=f"{definition.display_name} (schema validation)",
            backend_id="scp_lab.schema_validation.v1",
            execution_mode="schema_validation",
            provider="SCP-Lab reference implementation",
            state_schema=definition.state_schema,
        )
        self.capabilities = definition.capabilities
        for capability in self.capabilities:
            if capability.defaults_policy != "not_applied":
                raise ValueError("The offline backend requires defaults_policy=not_applied")

    async def execute(self, request: ExecutionRequest, context: ExecutionContext) -> BackendResult:
        return BackendResult(
            result={
                "validated_command": {
                    "model_id": self.description.model_id,
                    "capability_id": request.capability_id,
                    **request.arguments,
                },
                "source": self.source,
                "limitations": [
                    "Only the published parameter and resource-binding schemas were checked.",
                    "No vendor SDK, PyLabRobot backend or physical device was called.",
                    "Resource existence, layout, calibration and scientific effects are not verified.",
                ],
            },
            completion_evidence=CompletionEvidence(kind="schema_validation"),
        )


class OfflineOptions(Contract):
    model_resource: str | None = None
    model_file: str | None = None


def create_backend(config: DeviceConfig) -> DeviceBackend:
    """Reuse this factory with any model file that describes an offline validation interface."""
    Contract.model_validate(config.connection)
    options = OfflineOptions.model_validate(config.options)
    return OfflineBackend(load_model(**options.model_dump()), device_id=config.device_id)
