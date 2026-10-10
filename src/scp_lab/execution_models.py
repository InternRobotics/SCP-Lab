"""Transport-independent device invocation and local execution models."""

import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Contract(BaseModel):
    """Shared validation settings for SCP-Lab data models."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class ExecutionRequest(Contract):
    device_id: str = Field(min_length=1)
    capability_id: str = Field(min_length=1)
    arguments: dict
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=256)
    expected_descriptor_revision: str | None = None

    @model_validator(mode="after")
    def finite_json(self):
        json.dumps(self.arguments, allow_nan=False)
        return self


class Capability(Contract):
    capability_id: str = Field(min_length=1)
    version: str = "0.1.0"
    description: str
    input_schema: dict
    result_schema: dict = Field(default_factory=lambda: {"type": "object"})
    completion_criteria: str = "Backend returns evidence for the advertised execution mode."
    access_level: Literal["L1", "L2", "L3", "L4", "L5"] | None = None
    defaults_policy: Literal["not_applied", "backend_resolved"] = "not_applied"
    limitations: list[str] = Field(default_factory=list)


class DeviceDescription(Contract):
    """Static backend metadata; availability belongs to BackendState/DeviceState."""

    device_id: str = Field(min_length=1)
    model_id: str
    device_class: str
    display_name: str
    backend_id: str
    execution_mode: Literal["schema_validation", "official_simulation", "mock", "hardware"]
    physical_execution: bool = False
    cancellation_supported: bool = False
    provider: str | None = None
    configuration_version: str | None = None
    state_schema: dict | None = None

    @model_validator(mode="after")
    def physical_mode(self):
        if self.physical_execution != (self.execution_mode == "hardware"):
            raise ValueError("Only hardware backends may declare physical_execution=true")
        return self


class DeviceDescriptor(DeviceDescription):
    schema_version: Literal["scp-lab.device-descriptor.v0.1"] = "scp-lab.device-descriptor.v0.1"
    descriptor_revision: str
    capabilities: list[Capability]


class StateObservation(Contract):
    """Device-specific values; a query timestamp must not replace the observation timestamp."""

    values: dict
    observed_at: str
    source: str = Field(min_length=1)
    kind: Literal["measured", "device_reported", "simulated", "declared"]


class BackendState(Contract):
    # True means this configured backend accepts work, not that physical readiness was measured.
    available: bool = True
    availability_message: str | None = None
    observation: StateObservation | None = None


class DeviceState(BackendState):
    schema_version: Literal["scp-lab.device-state.v0.1"] = "scp-lab.device-state.v0.1"
    device_id: str
    state: Literal["idle", "busy", "unavailable", "needs_attention"]
    active_run_id: str | None = None
    reported_at: str
    source: Literal["local_execution_runtime"] = "local_execution_runtime"
    scope: Literal["this_server_process"] = "this_server_process"


class ExecutionError(Contract):
    code: str
    message: str
    details: dict = Field(default_factory=dict)


class CompletionEvidence(Contract):
    kind: str = "none"
    physical_completion_verified: bool = False
    details: dict = Field(default_factory=dict)


class BackendResult(Contract):
    status: Literal["succeeded", "failed", "cancelled", "unknown"] = "succeeded"
    result: dict = Field(default_factory=dict)
    completion_evidence: CompletionEvidence = Field(default_factory=CompletionEvidence)
    error: ExecutionError | None = None
    device_released: bool | None = None


class ExecutionRecord(Contract):
    schema_version: Literal["scp-lab.execution.v0.1"] = "scp-lab.execution.v0.1"
    run_id: str
    request: ExecutionRequest
    descriptor_revision: str
    capability_version: str
    effective_arguments: dict
    backend_id: str
    execution_mode: str
    physical_execution: bool
    status: Literal[
        "accepted", "running", "cancel_requested", "succeeded", "failed", "cancelled", "unknown"
    ] = "accepted"
    submitted_at: str
    updated_at: str
    started_at: str | None = None
    finished_at: str | None = None
    progress: dict = Field(default_factory=dict)
    result: dict = Field(default_factory=dict)
    completion_evidence: CompletionEvidence = Field(default_factory=CompletionEvidence)
    error: ExecutionError | None = None
    device_released: bool = False


class ProtocolError(ValueError):
    def __init__(self, code: str, message: str, **details):
        super().__init__(message)
        self.error = ExecutionError(code=code, message=message, details=details)
