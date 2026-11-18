"""Opentrons OT-2 and Flex rail-light control over the robot server's local HTTP API."""

import asyncio
from http.client import HTTPException

from scp_lab.adapters.schemas import load_model
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

from ..http_api import ServiceConnection


class RailLightsBackend(DeviceBackend):
    def __init__(self, config: DeviceConfig):
        self.connection = ServiceConnection.model_validate(config.connection)
        Contract.model_validate(config.options)
        model = load_model(model_resource=f"{__package__}:models/rail_lights.json").definition
        self.capabilities = model.capabilities
        self.description = DeviceDescription(
            device_id=config.device_id,
            model_id=model.model_id,
            device_class=model.device_class,
            display_name=model.display_name,
            backend_id="example.opentrons.rail_lights",
            execution_mode="hardware",
            physical_execution=True,
        )

    def _request(self, method: str, on: bool | None = None) -> bool:
        data = self.connection.request(
            method,
            "/robot/lights",
            payload={"on": on} if on is not None else None,
            headers={"Opentrons-Version": "2"},
        )
        if not isinstance(data, dict) or not isinstance(data.get("on"), bool):
            raise ValueError(f"{method} /robot/lights returned an invalid light state")
        return data["on"]

    async def execute(self, request: ExecutionRequest, context: ExecutionContext) -> BackendResult:
        setting = request.capability_id == "opentrons.set_rail_lights"
        try:
            if setting:
                await asyncio.to_thread(self._request, "POST", request.arguments["on"])
            observed = await asyncio.to_thread(self._request, "GET")
        except (OSError, HTTPException, ValueError) as error:
            # A lost POST response or readback leaves the outcome of a write unknown.
            return BackendResult(
                status="unknown" if setting else "failed",
                error=ExecutionError(code="rail_lights_request_error", message=str(error)),
                device_released=not setting,
            )

        result = BackendResult(
            result={"on": observed},
            completion_evidence=CompletionEvidence(
                kind="device_reported", details={"source": "GET /robot/lights", "on": observed}
            ),
            device_released=True,
        )
        if setting and observed != request.arguments["on"]:
            result.status = "failed"
            result.error = ExecutionError(
                code="rail_lights_mismatch", message="Readback differs from the requested state"
            )
        return result


def create_backend(config: DeviceConfig) -> DeviceBackend:
    return RailLightsBackend(config)
