"""Backend authoring API. A backend executes explicit requests, never plans experiments."""

import asyncio
from abc import ABC, abstractmethod
from collections.abc import Callable
from copy import deepcopy

from jsonschema import Draft202012Validator

from .execution_models import (
    BackendResult,
    BackendState,
    Capability,
    DeviceDescription,
    ExecutionRequest,
    ProtocolError,
)


class ExecutionContext:
    def __init__(self, cancel_event: asyncio.Event, report_progress: Callable[[dict], None]):
        self.cancel_event = cancel_event
        self.report_progress = report_progress

    async def wait(self, seconds: float) -> bool:
        """Return True on a cancellation request, False after the requested wait."""
        try:
            await asyncio.wait_for(self.cancel_event.wait(), timeout=seconds)
            return True
        except asyncio.TimeoutError:
            return False


class DeviceBackend(ABC):
    description: DeviceDescription
    capabilities: list[Capability]

    def read_state(self) -> BackendState:
        """Return current local availability and optional cached observations; no device action."""
        return BackendState()

    def resolve_arguments(self, request: ExecutionRequest) -> dict:
        """Optionally resolve published defaults before acceptance; never perform device actions."""
        return deepcopy(request.arguments)

    def validate(self, request: ExecutionRequest) -> None:
        capability = next(
            (c for c in self.capabilities if c.capability_id == request.capability_id), None
        )
        if capability is None:
            raise ProtocolError("unknown_capability", "Capability is not exposed by this device")
        errors = list(Draft202012Validator(capability.input_schema).iter_errors(request.arguments))
        if errors:
            error = errors[0]
            raise ProtocolError("invalid_arguments", error.message, path=list(error.absolute_path))

    @abstractmethod
    async def execute(self, request: ExecutionRequest, context: ExecutionContext) -> BackendResult:
        """Return observed outcomes; cancellation requests must not imply physical completion."""
