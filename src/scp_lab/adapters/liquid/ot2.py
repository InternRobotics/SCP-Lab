"""OT-2 compilation and official simulation adapter."""

import asyncio
import importlib.util
import os
from pathlib import Path

from scp_lab.backend import DeviceBackend, ExecutionContext
from scp_lab.compiler import compile_protocol
from scp_lab.device_config import DeviceConfig
from scp_lab.execution_models import (
    BackendResult,
    BackendState,
    CompletionEvidence,
    Contract,
    DeviceDescription,
    ExecutionError,
    ExecutionRequest,
)
from scp_lab.models import Protocol
from scp_lab.simulation import simulate_protocol

from .ot2_schemas import OT2Arguments, get_capabilities


def ot2_protocol(request: ExecutionRequest) -> Protocol:
    args = OT2Arguments.model_validate(request.arguments)
    if {"id", "action"}.intersection(args.parameters):
        raise ValueError("parameters must not contain id or action")
    return Protocol.model_validate(
        {
            "name": request.capability_id,
            "experiment_id": "single-capability",
            "setup": args.setup.model_dump(),
            "liquids": [item.model_dump() for item in args.liquids],
            "steps": [
                {
                    "id": "call",
                    "action": request.capability_id.removeprefix("ot2."),
                    **args.parameters,
                }
            ],
        }
    )


class OT2SimulationBackend(DeviceBackend):
    def __init__(self, device_id="ot2-sim"):
        self.description = DeviceDescription(
            device_id=device_id,
            model_id="ot2",
            device_class="liquid",
            display_name="OT-2 official simulator",
            backend_id="scp_lab.opentrons.v1",
            execution_mode="official_simulation",
            provider="SCP-Lab reference implementation",
        )
        self.capabilities = get_capabilities()

    def read_state(self) -> BackendState:
        interpreter = os.environ.get("SCP_LAB_SIM_PYTHON")
        configured = (
            Path(interpreter).is_file()
            if interpreter
            else importlib.util.find_spec("opentrons") is not None
        )
        return BackendState(
            available=configured,
            availability_message=(
                "Interpreter configured; SDK version checked at execution."
                if configured
                else "Set SCP_LAB_SIM_PYTHON to the simulator Python."
            ),
        )

    def resolve_arguments(self, request: ExecutionRequest) -> dict:
        protocol = ot2_protocol(request)
        return {
            "setup": protocol.setup.model_dump(),
            "liquids": [liquid.model_dump() for liquid in protocol.liquids],
            "parameters": protocol.steps[0].model_dump(exclude={"id", "action"}),
        }

    def validate(self, request: ExecutionRequest) -> None:
        super().validate(request)
        compile_protocol(ot2_protocol(request))

    async def execute(self, request: ExecutionRequest, context: ExecutionContext) -> BackendResult:
        record = await asyncio.to_thread(simulate_protocol, ot2_protocol(request))
        succeeded = record["status"] == "succeeded"
        return BackendResult(
            status="succeeded" if succeeded else "failed",
            result=record,
            completion_evidence=CompletionEvidence(
                kind="official_simulator_runlog" if succeeded else "none",
                details={"simulation_run_id": record["run_id"]},
            ),
            error=None
            if succeeded
            else ExecutionError(
                code="simulation_failed"
                if record["status"] != "unavailable"
                else "backend_unavailable",
                message=str(record.get("error", "Simulation failed")),
            ),
        )


def create_backend(config: DeviceConfig) -> DeviceBackend:
    """The simulator environment is selected by SCP_LAB_SIM_PYTHON."""
    Contract.model_validate(config.connection)
    Contract.model_validate(config.options)
    return OT2SimulationBackend(device_id=config.device_id)
