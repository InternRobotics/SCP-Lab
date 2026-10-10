"""One-process local execution layer. No agent, shared-device distributed lock or durable queue."""

import asyncio
import json
from datetime import datetime, timezone
from hashlib import sha256
from uuid import uuid4

from jsonschema import Draft202012Validator

from .backend import DeviceBackend, ExecutionContext
from .execution_models import (
    BackendResult,
    BackendState,
    DeviceDescriptor,
    DeviceState,
    ExecutionError,
    ExecutionRecord,
    ExecutionRequest,
    ProtocolError,
)
from .schema_metadata import check_schema

TERMINAL = {"succeeded", "failed", "cancelled", "unknown"}


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


class LocalExecutionRuntime:
    def __init__(self, backends: list[DeviceBackend]):
        self.backends = {}
        self.descriptors: dict[str, DeviceDescriptor] = {}
        for backend in backends:
            device_id = backend.description.device_id
            if device_id in self.backends:
                raise ValueError(f"Duplicate device instance: {device_id}")
            ids = [c.capability_id for c in backend.capabilities]
            if len(ids) != len(set(ids)):
                raise ValueError(f"Duplicate capability ID on {device_id}")
            for capability in backend.capabilities:
                check_schema(capability.input_schema)
                check_schema(capability.result_schema)
            if backend.description.state_schema is not None:
                check_schema(backend.description.state_schema)
            descriptor = DeviceDescriptor(
                **backend.description.model_dump(),
                descriptor_revision="pending",
                capabilities=[c.model_copy(deep=True) for c in backend.capabilities],
            )
            content = json.dumps(
                descriptor.model_dump(exclude={"descriptor_revision"}),
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
            descriptor.descriptor_revision = "sha256:" + sha256(content.encode()).hexdigest()
            self.descriptors[device_id] = descriptor
            self.backends[device_id] = backend
        self.runs: dict[str, ExecutionRecord] = {}
        self.active: dict[str, str] = {}
        self.keys: dict[tuple[str, str], tuple[str, str]] = {}
        self.cancel_events: dict[str, asyncio.Event] = {}
        self.tasks: dict[str, asyncio.Task] = {}
        self.lock = asyncio.Lock()

    def _backend(self, device_id):
        if device_id not in self.backends:
            raise ProtocolError(
                "unknown_device", "Device instance is not registered", device_id=device_id
            )
        return self.backends[device_id]

    def device_state(self, device_id: str) -> dict:
        backend = self._backend(device_id)
        try:
            state = BackendState.model_validate(backend.read_state())
            json.dumps(state.model_dump(), allow_nan=False)
            if state.observation is not None:
                schema = self.descriptors[device_id].state_schema
                if schema is None:
                    raise ValueError("Observed values require a published state_schema")
                Draft202012Validator(schema).validate(state.observation.values)
        except Exception as error:
            raise ProtocolError("invalid_backend_state", str(error), device_id=device_id) from error
        active = self.active.get(device_id)
        return DeviceState(
            **state.model_dump(),
            device_id=device_id,
            state=(
                "needs_attention"
                if active and self.runs[active].status in TERMINAL
                else "busy"
                if active
                else "idle"
                if state.available
                else "unavailable"
            ),
            active_run_id=active,
            reported_at=timestamp(),
        ).model_dump(mode="json")

    def list_devices(self, device_class: str | None = None) -> list[dict]:
        return [
            {
                **descriptor.model_dump(exclude={"capabilities", "state_schema", "schema_version"}),
                "state": self.device_state(device_id),
                "capability_count": len(descriptor.capabilities),
            }
            for device_id, descriptor in self.descriptors.items()
            if device_class is None or descriptor.device_class == device_class
        ]

    def describe_device(self, device_id: str) -> dict:
        self._backend(device_id)
        return self.descriptors[device_id].model_dump(mode="json")

    def get_execution(self, run_id: str) -> dict:
        if run_id not in self.runs:
            raise ProtocolError(
                "unknown_run", "Run does not exist in this server process", run_id=run_id
            )
        return self.runs[run_id].model_dump(mode="json")

    async def submit(self, request: ExecutionRequest) -> dict:
        # Own the payload: an embedding application must not mutate an accepted request later.
        request = request.model_copy(deep=True)
        backend = self._backend(request.device_id)
        descriptor = self.descriptors[request.device_id]
        fingerprint = json.dumps(
            request.model_dump(exclude={"idempotency_key"}), sort_keys=True, allow_nan=False
        )
        key = (request.device_id, request.idempotency_key) if request.idempotency_key else None
        async with self.lock:
            if key in self.keys:
                previous, run_id = self.keys[key]
                if previous != fingerprint:
                    raise ProtocolError(
                        "idempotency_conflict", "Key was already used with different arguments"
                    )
                return self.get_execution(run_id)
            if (
                request.expected_descriptor_revision is not None
                and request.expected_descriptor_revision != descriptor.descriptor_revision
            ):
                raise ProtocolError("descriptor_changed", "Discover the current descriptor again")
            state = self.device_state(request.device_id)
            if not state["available"]:
                raise ProtocolError(
                    "backend_unavailable", state["availability_message"] or "Unavailable"
                )
            try:
                # Required fields still apply: JSON Schema defaults do not make them optional.
                DeviceBackend.validate(backend, request)
                capability = next(
                    c for c in descriptor.capabilities if c.capability_id == request.capability_id
                )
                prepared = request.model_copy(deep=True)
                prepared.arguments = backend.resolve_arguments(request.model_copy(deep=True))
                prepared = ExecutionRequest.model_validate(prepared.model_dump())
                if (
                    capability.defaults_policy == "not_applied"
                    and prepared.arguments != request.arguments
                ):
                    raise ProtocolError(
                        "invalid_backend_defaults",
                        "Backend changed arguments without declaring resolution",
                    )
                backend.validate(prepared)
            except ProtocolError:
                raise
            except ValueError as error:
                raise ProtocolError("invalid_arguments", str(error)) from error
            if request.device_id in self.active:
                raise ProtocolError(
                    "device_busy",
                    "Device has an active or unresolved execution",
                    active_run_id=self.active[request.device_id],
                )
            run_id = str(uuid4())
            now = timestamp()
            record = ExecutionRecord(
                run_id=run_id,
                request=request,
                descriptor_revision=descriptor.descriptor_revision,
                capability_version=capability.version,
                effective_arguments=prepared.arguments,
                backend_id=descriptor.backend_id,
                execution_mode=descriptor.execution_mode,
                physical_execution=descriptor.physical_execution,
                submitted_at=now,
                updated_at=now,
            )
            self.runs[run_id] = record
            self.active[request.device_id] = run_id
            self.cancel_events[run_id] = asyncio.Event()
            if key:
                self.keys[key] = (fingerprint, run_id)
            self.tasks[run_id] = asyncio.create_task(
                self._execute(backend, record, prepared, capability)
            )
            return self.get_execution(run_id)

    async def _execute(self, backend, record, prepared, capability):
        event = self.cancel_events[record.run_id]
        if record.status != "cancel_requested":
            record.status = "running"
        record.started_at = timestamp()
        record.updated_at = record.started_at

        def progress(value):
            json.dumps(value, allow_nan=False)
            record.progress = dict(value)
            record.updated_at = timestamp()

        try:
            outcome = await backend.execute(
                prepared.model_copy(deep=True), ExecutionContext(event, progress)
            )
            outcome = BackendResult.model_validate(outcome)
            json.dumps(outcome.model_dump(), allow_nan=False)
            if outcome.status == "succeeded":
                Draft202012Validator(capability.result_schema).validate(outcome.result)
                if outcome.completion_evidence.kind == "none":
                    raise ValueError("Successful execution must identify its completion evidence")
            if (
                not record.physical_execution
                and outcome.completion_evidence.physical_completion_verified
            ):
                raise ValueError("Non-hardware backends cannot confirm physical completion")
            record.status = outcome.status
            record.result = outcome.result
            record.completion_evidence = outcome.completion_evidence
            record.error = outcome.error
            record.device_released = outcome.status != "unknown" and (
                outcome.device_released
                if outcome.device_released is not None
                else not record.physical_execution
            )
        except asyncio.CancelledError:
            # Process shutdown is not evidence that a device stopped.
            record.status = "unknown"
            record.error = ExecutionError(
                code="execution_interrupted", message="Local execution was interrupted"
            )
            raise
        except Exception as error:
            record.status = "unknown" if record.physical_execution else "failed"
            record.error = ExecutionError(
                code="backend_error",
                message=str(error),
                details={"exception_type": type(error).__name__},
            )
            record.device_released = not record.physical_execution
        finally:
            record.finished_at = timestamp()
            record.updated_at = record.finished_at
            if record.device_released:
                self.active.pop(record.request.device_id, None)

    async def cancel(self, run_id: str) -> dict:
        self.get_execution(run_id)
        record = self.runs[run_id]
        if record.status in TERMINAL:
            return self.get_execution(run_id)
        backend = self._backend(record.request.device_id)
        if not self.descriptors[backend.description.device_id].cancellation_supported:
            raise ProtocolError("cancellation_unsupported", "Backend cannot confirm cancellation")
        record.status = "cancel_requested"
        record.updated_at = timestamp()
        self.cancel_events[run_id].set()
        return self.get_execution(run_id)

    async def aclose(self):
        for run_id, task in self.tasks.items():
            record = self.runs[run_id]
            if (
                not task.done()
                and self.backends[record.request.device_id].description.cancellation_supported
            ):
                self.cancel_events[run_id].set()
        if self.tasks:
            await asyncio.gather(*self.tasks.values(), return_exceptions=True)
