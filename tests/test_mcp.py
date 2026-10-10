import asyncio
import json
import os
import sys

import pytest
from jsonschema import Draft202012Validator
from test_protocol import load


@pytest.mark.mcp
def test_stdio_client_server(tmp_path):
    pytest.importorskip("mcp")
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    async def scenario():
        env = {"SCP_LAB_RUN_DIR": str(tmp_path)}
        if os.environ.get("SCP_LAB_SIM_PYTHON"):
            env["SCP_LAB_SIM_PYTHON"] = os.environ["SCP_LAB_SIM_PYTHON"]
        server = StdioServerParameters(
            command=sys.executable, args=["-m", "scp_lab.server"], env=env
        )
        async with stdio_client(server) as (read, write):
            async with ClientSession(read, write) as client:
                await client.initialize()
                tools = (await client.list_tools()).tools
                names = {t.name for t in tools}
                assert {"capabilities", "invoke_capability", "simulate_protocol"} <= names
                for tool in tools:
                    assert tool.outputSchema is not None, tool.name
                    Draft202012Validator.check_schema(tool.outputSchema)
                result = await client.call_tool("capabilities", {})
                assert not result.isError
                catalog = result.structuredContent
                assert catalog == json.loads(result.content[0].text)
                assert len(catalog["capabilities"]) == 9
                result = await client.call_tool("compile_protocol", {"protocol": load()})
                assert not result.isError
                payload = result.structuredContent or json.loads(result.content[0].text)
                assert "pipette.aspirate" in payload["code"]
                result = await client.call_tool(
                    "invoke_capability",
                    {
                        "capability_id": "ot2.liquid_transfer",
                        "setup": load()["setup"],
                        "liquids": load()["liquids"],
                        "parameters": {
                            "source": {"labware": "plate", "well": "A1"},
                            "destination": {"labware": "plate", "well": "B1"},
                            "volume_ul": 50,
                        },
                    },
                )
                assert not result.isError
                invalid = load()
                invalid["steps"][1]["volume_ul"] = -1
                assert (await client.call_tool("validate_protocol", {"protocol": invalid})).isError
                result = await client.read_resource("scp-lab://schemas/protocol")
                assert "schema_version" in result.contents[0].text
                for name in ("device-descriptor", "device-state", "execution-record"):
                    resource = await client.read_resource(f"scp-lab://schemas/{name}")
                    schema = json.loads(resource.contents[0].text)
                    assert "schema_version" in schema["properties"]
                if "SCP_LAB_SIM_PYTHON" in env:
                    result = await client.call_tool("simulate_protocol", {"protocol": load()})
                    assert not result.isError
                    payload = result.structuredContent or json.loads(result.content[0].text)
                    assert payload["status"] == "succeeded", payload
                    result = await client.call_tool(
                        "read_simulation_run", {"run_id": payload["run_id"]}
                    )
                    assert not result.isError

    asyncio.run(scenario())


@pytest.mark.mcp
def test_device_tool_envelopes_and_execution_failure(tmp_path):
    pytest.importorskip("mcp")
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    async def scenario():
        server = StdioServerParameters(
            command=sys.executable,
            args=["-m", "scp_lab.server"],
            env={"SCP_LAB_RUN_DIR": str(tmp_path)},
        )
        async with stdio_client(server) as (read, write):
            async with ClientSession(read, write) as client:
                await client.initialize()
                schemas = {
                    tool.name: tool.outputSchema for tool in (await client.list_tools()).tools
                }

                async def call(name, arguments, error=None):
                    result = await client.call_tool(name, arguments)
                    assert result.isError is (error is not None)
                    payload = result.structuredContent
                    assert payload == json.loads(result.content[0].text)
                    Draft202012Validator(schemas[name]).validate(payload)
                    if error:
                        assert payload["ok"] is False
                        assert payload["error"]["code"] == error
                        return payload["error"]
                    assert payload["ok"] is True
                    return payload["data"]

                devices = await call("list_devices", {})
                assert any(device["device_id"] == "demo-heater" for device in devices)
                await call("describe_device", {"device_id": "demo-heater"})
                await call("get_device_state", {"device_id": "demo-heater"})
                for name in ("describe_device", "get_device_state"):
                    error = await call(name, {"device_id": "absent"}, "unknown_device")
                    assert error["details"]["device_id"] == "absent"
                for name in ("get_execution", "cancel_execution"):
                    await call(name, {"run_id": "absent"}, "unknown_run")

                request = {
                    "device_id": "demo-heater-fault",
                    "capability_id": "demo_heater.hold",
                    "arguments": {"target_celsius": 37, "duration_s": 0.02},
                }
                await call(
                    "submit_execution",
                    {"request": {**request, "arguments": {"target_celsius": 1000}}},
                    "invalid_arguments",
                )
                # Input validation by the MCP SDK need not use the SCP-Lab error envelope.
                malformed = await client.call_tool("submit_execution", {"request": {}})
                assert malformed.isError

                record = await call("submit_execution", {"request": request})

                async def wait_for_failure():
                    while True:
                        current = await call("get_execution", {"run_id": record["run_id"]})
                        if current["status"] == "failed":
                            return current
                        await asyncio.sleep(0.01)

                failed = await asyncio.wait_for(wait_for_failure(), timeout=5)
                assert failed["error"]["code"] == "demo_heater_fault"
                await call("cancel_execution", {"run_id": record["run_id"]})

    asyncio.run(scenario())


@pytest.mark.mcp
def test_simulation_call_failure_and_record_lookup(tmp_path):
    pytest.importorskip("mcp")
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    async def scenario():
        server = StdioServerParameters(
            command=sys.executable,
            args=["-m", "scp_lab.server"],
            env={
                "SCP_LAB_RUN_DIR": str(tmp_path),
                "SCP_LAB_SIM_PYTHON": str(tmp_path / "missing-simulator"),
            },
        )
        async with stdio_client(server) as (read, write):
            async with ClientSession(read, write) as client:
                await client.initialize()
                result = await client.call_tool("simulate_protocol", {"protocol": load()})
                assert result.isError
                record = result.structuredContent
                assert record == json.loads(result.content[0].text)
                assert record["status"] == "failed"
                retrieved = await client.call_tool(
                    "read_simulation_run", {"run_id": record["run_id"]}
                )
                assert not retrieved.isError
                assert retrieved.structuredContent == record

    asyncio.run(scenario())
