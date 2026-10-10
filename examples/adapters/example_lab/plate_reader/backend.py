"""One reusable reader adapter; instance identity and settings come from device JSON."""

from datetime import datetime, timezone

from pydantic import Field

from scp_lab.backend import DeviceBackend, ExecutionContext
from scp_lab.device_config import DeviceConfig
from scp_lab.execution_models import (
    BackendResult,
    BackendState,
    CompletionEvidence,
    Contract,
    DeviceDescription,
    ExecutionRequest,
    StateObservation,
)

from .schemas import get_model


class DemonstrationReaderSDK:
    """No device connection: returns explicitly synthetic readings."""

    def __init__(self, absorbance):
        self.absorbance = absorbance

    async def read_absorbance(self, plate_id, wavelength_nm):
        return {
            "plate_id": plate_id,
            "wavelength_nm": wavelength_nm,
            "values": {"A1": self.absorbance},
            "unit": "AU",
            "synthetic": True,
        }


class MyReaderBackend(DeviceBackend):
    def __init__(self, config: DeviceConfig, sdk):
        model = get_model()
        self.sdk = sdk
        self.observation = None
        self.description = DeviceDescription(
            device_id=config.device_id,
            model_id=model.model_id,
            device_class=model.device_class,
            display_name=model.display_name,
            backend_id="example.reader.v1",
            execution_mode="mock",
            state_schema=model.state_schema,
        )
        self.capabilities = model.capabilities

    def read_state(self) -> BackendState:
        return BackendState(observation=self.observation)

    async def execute(self, request: ExecutionRequest, context: ExecutionContext) -> BackendResult:
        context.report_progress({"stage": "reading"})
        reading = await self.sdk.read_absorbance(**request.arguments)
        self.observation = StateObservation(
            values={"last_plate_id": request.arguments["plate_id"]},
            observed_at=datetime.now(timezone.utc).isoformat(),
            source="demonstration_reader_sdk",
            kind="simulated",
        )
        return BackendResult(
            result=reading, completion_evidence=CompletionEvidence(kind="mock_trace")
        )


class ReaderOptions(Contract):
    synthetic_absorbance: float = Field(default=0.123, ge=0, le=5)


def create_backend(config: DeviceConfig) -> DeviceBackend:
    # This mock has no connection settings. A hardware adapter validates its own
    # connection schema here, then creates its SDK client from those settings.
    Contract.model_validate(config.connection)
    options = ReaderOptions.model_validate(config.options)
    return MyReaderBackend(config, DemonstrationReaderSDK(options.synthetic_absorbance))
