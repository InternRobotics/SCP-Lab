"""Read Bioyond Studio scheduler status through its LIMS service."""

import asyncio
from datetime import datetime, timezone
from http.client import HTTPException
from pathlib import Path

from pydantic import field_validator

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


class BioyondConnection(ServiceConnection):
    api_key_file: Path

    @field_validator("api_key_file")
    @classmethod
    def absolute_path(cls, path):
        if not path.is_absolute():
            raise ValueError("api_key_file must be an absolute path")
        return path


class SchedulerBackend(DeviceBackend):
    def __init__(self, config: DeviceConfig):
        self.connection = BioyondConnection.model_validate(config.connection)
        Contract.model_validate(config.options)
        model = load_model(model_resource=f"{__package__}:models/scheduler.json").definition
        self.capabilities = model.capabilities
        self.description = DeviceDescription(
            device_id=config.device_id,
            model_id=model.model_id,
            device_class=model.device_class,
            display_name=model.display_name,
            backend_id="example.bioyond.scheduler",
            execution_mode="hardware",
            physical_execution=True,
        )

    def _read_status(self) -> str:
        key = self.connection.api_key_file.read_text(encoding="utf-8").strip()
        if not key:
            raise ValueError("Empty Bioyond API key file")
        timestamp = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        response = self.connection.request(
            "POST",
            "/api/lims/scheduler/scheduler-status",
            payload={"apiKey": key, "requestTime": timestamp.replace("+00:00", "Z")},
        )
        if (
            not isinstance(response, dict)
            or type(response.get("code")) is not int
            or response["code"] != 1
        ):
            raise ValueError("Bioyond service did not report success")
        data = response.get("data")
        if (
            not isinstance(data, dict)
            or not isinstance(data.get("schedulerStatus"), str)
            or not data["schedulerStatus"].strip()
        ):
            raise ValueError("Bioyond response lacks a scheduler status")
        return data["schedulerStatus"]

    async def execute(self, request: ExecutionRequest, context: ExecutionContext) -> BackendResult:
        try:
            status = await asyncio.to_thread(self._read_status)
        except (ValueError, HTTPException, OSError) as error:
            return BackendResult(
                status="failed",
                error=ExecutionError(code="scheduler_status_error", message=str(error)),
                device_released=True,
            )
        return BackendResult(
            result={"schedulerStatus": status},
            completion_evidence=CompletionEvidence(
                kind="device_reported", details={"source": "Bioyond Studio scheduler"}
            ),
            device_released=True,
        )


def create_backend(config: DeviceConfig) -> DeviceBackend:
    return SchedulerBackend(config)
