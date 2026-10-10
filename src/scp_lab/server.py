"""MCP binding for device access and a configurable local execution layer."""

import asyncio
import json
from contextlib import asynccontextmanager
from typing import Annotated, Any, Literal

from .capabilities import list_capabilities, protocol_schema, supported_labware
from .compiler import compile_protocol as compile_request
from .execution_models import (
    DeviceDescriptor,
    DeviceState,
    ExecutionRecord,
    ExecutionRequest,
    ProtocolError,
)
from .mcp_models import DeviceResponse
from .models import InitialLiquid, Protocol, Setup
from .registry import create_runtime
from .simulation import get_run
from .simulation import simulate_protocol as simulate_request
from .validation import validate


def create_server(devices_dir=None):
    from mcp.server.fastmcp import FastMCP
    from mcp.types import CallToolResult, TextContent

    runtime = create_runtime(devices_dir)

    @asynccontextmanager
    async def lifespan(_server):
        try:
            yield runtime
        finally:
            await runtime.aclose()

    server = FastMCP(
        "SCP-Lab",
        instructions="Discover local device instances with list_devices, inspect each device's capability schemas with describe_device, submit explicit executions and query their status. Execution mode and completion evidence specify what was actually checked. Built-in devices use schema validation, mock execution or official simulation; custom backends are configured locally. No agent or experiment planner is provided.",
        lifespan=lifespan,
        log_level="WARNING",
    )

    def tool_result(payload, *, is_error=False):
        return CallToolResult(
            content=[
                TextContent(
                    type="text", text=json.dumps(payload, ensure_ascii=False, allow_nan=False)
                )
            ],
            structuredContent=payload,
            isError=is_error,
        )

    def response(function, *args):
        try:
            return tool_result({"ok": True, "data": function(*args)})
        except ProtocolError as error:
            return tool_result({"ok": False, "error": error.error.model_dump()}, is_error=True)

    async def async_response(function, *args):
        try:
            return tool_result({"ok": True, "data": await function(*args)})
        except ProtocolError as error:
            return tool_result({"ok": False, "error": error.error.model_dump()}, is_error=True)

    @server.tool()
    def list_devices(
        device_class: str | None = None,
    ) -> Annotated[CallToolResult, DeviceResponse[list[dict[str, Any]]]]:
        """Discover configured device instances, execution modes and local availability."""
        return response(runtime.list_devices, device_class)

    @server.tool()
    def describe_device(
        device_id: str,
    ) -> Annotated[CallToolResult, DeviceResponse[DeviceDescriptor]]:
        """Get the static descriptor, revision and capability schemas; query live state separately."""
        return response(runtime.describe_device, device_id)

    @server.tool()
    def get_device_state(device_id: str) -> Annotated[CallToolResult, DeviceResponse[DeviceState]]:
        """Read local occupancy/availability and optional source-labelled device observations."""
        return response(runtime.device_state, device_id)

    @server.tool()
    async def submit_execution(
        request: ExecutionRequest,
    ) -> Annotated[CallToolResult, DeviceResponse[ExecutionRecord]]:
        """Validate and accept an explicit device call; return a run ID before execution completes."""
        return await async_response(runtime.submit, request)

    @server.tool()
    def get_execution(run_id: str) -> Annotated[CallToolResult, DeviceResponse[ExecutionRecord]]:
        """Read task status, result, errors and evidence within the same server session."""
        return response(runtime.get_execution, run_id)

    @server.tool()
    async def cancel_execution(
        run_id: str,
    ) -> Annotated[CallToolResult, DeviceResponse[ExecutionRecord]]:
        """Request cooperative cancellation when advertised; poll until its actual outcome is known."""
        return await async_response(runtime.cancel, run_id)

    @server.tool()
    def capabilities() -> dict[str, Any]:
        """Get implemented OT-2 capabilities, parameter schemas and supported labware."""
        return {"capabilities": list_capabilities(), "labware": supported_labware()}

    @server.tool()
    def validate_protocol(protocol: Protocol) -> dict[str, Any]:
        """Check setup, parameters, tips and declared liquid balances without the SDK."""
        return validate(protocol)

    @server.tool()
    def compile_protocol(protocol: Protocol) -> dict[str, Any]:
        """Generate reviewable OT-2 Python code after static preflight."""
        return compile_request(protocol)

    @server.tool()
    async def simulate_protocol(protocol: Protocol) -> Annotated[CallToolResult, dict[str, Any]]:
        """Run the optional official simulator and retain its run record. Never uses hardware."""
        record = await asyncio.to_thread(simulate_request, protocol)
        return tool_result(record, is_error=record["status"] != "succeeded")

    @server.tool()
    async def invoke_capability(
        capability_id: str,
        setup: Setup,
        parameters: dict,
        liquids: list[InitialLiquid],
        mode: Literal["compile", "simulate"] = "compile",
    ) -> Annotated[CallToolResult, dict[str, Any]]:
        """Invoke one catalog capability using its input schema and explicit setup/liquid state."""
        known = {c["capability_id"] for c in list_capabilities()}
        if capability_id not in known:
            raise ValueError(
                "Capability is not implemented; use capabilities to discover supported IDs"
            )
        if {"id", "action"}.intersection(parameters):
            raise ValueError("parameters must not contain reserved id or action fields")
        action = capability_id.removeprefix("ot2.")
        protocol = Protocol.model_validate(
            {
                "name": capability_id,
                "experiment_id": "single-capability",
                "setup": setup.model_dump(),
                "liquids": [x.model_dump() for x in liquids],
                "steps": [{"id": "call", "action": action, **parameters}],
            }
        )
        if mode == "compile":
            return tool_result(compile_request(protocol))
        record = await asyncio.to_thread(simulate_request, protocol)
        return tool_result(record, is_error=record["status"] != "succeeded")

    @server.tool()
    def read_simulation_run(run_id: str) -> dict[str, Any]:
        """Read a completed, failed or unavailable simulation record by ID."""
        return get_run(run_id)

    @server.resource("scp-lab://schemas/protocol")
    def schema() -> str:
        import json

        return json.dumps(protocol_schema())

    @server.resource("scp-lab://schemas/execution-request")
    def execution_request_schema() -> str:
        import json

        return json.dumps(ExecutionRequest.model_json_schema())

    @server.resource("scp-lab://schemas/execution-record")
    def execution_record_schema() -> str:
        import json

        return json.dumps(ExecutionRecord.model_json_schema())

    @server.resource("scp-lab://schemas/device-descriptor")
    def device_descriptor_schema() -> str:
        import json

        return json.dumps(DeviceDescriptor.model_json_schema())

    @server.resource("scp-lab://schemas/device-state")
    def device_state_schema() -> str:
        import json

        return json.dumps(DeviceState.model_json_schema())

    return server


def main(devices_dir=None):
    create_server(devices_dir).run(transport="stdio")


if __name__ == "__main__":
    main()
