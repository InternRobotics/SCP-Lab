"""Small ordinary MCP client shared by the examples. No model or agent."""

import asyncio
import json
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

TERMINAL = {"succeeded", "failed", "cancelled", "unknown"}
ROOT = Path(__file__).resolve().parents[1]


@asynccontextmanager
async def connect(extra_env=None):
    env = {
        k: os.environ[k]
        for k in ("SCP_LAB_SIM_PYTHON", "SCP_LAB_RUN_DIR", "SCP_LAB_DEVICES_DIR")
        if k in os.environ
    }
    # This client owns one persistent server session for submission, polling and cancellation.
    async with stdio_client(
        StdioServerParameters(
            command=sys.executable,
            args=["-m", "scp_lab.server"],
            env={**env, **(extra_env or {})},
        )
    ) as (read, write):
        async with ClientSession(read, write) as client:
            await client.initialize()
            yield client


async def call(client, name, arguments=None, *, expected_error=None):
    result = await client.call_tool(name, arguments or {})
    if result.isError and not expected_error:
        raise RuntimeError(result.content)
    payload = result.structuredContent or json.loads(result.content[0].text)
    if expected_error:
        assert result.isError, payload
        assert not payload["ok"] and payload["error"]["code"] == expected_error, payload
        return payload["error"]
    if not payload["ok"]:
        raise RuntimeError(payload["error"])
    return payload["data"]


async def wait_for_run(client, run_id, timeout=70, *, show_status=False):
    deadline = asyncio.get_running_loop().time() + timeout
    previous_status = None
    while asyncio.get_running_loop().time() < deadline:
        record = await call(client, "get_execution", {"run_id": run_id})
        if show_status and record["status"] != previous_status:
            print(f"get_execution -> {record['status']}", flush=True)
        previous_status = record["status"]
        if record["status"] in TERMINAL:
            return record
        await asyncio.sleep(0.2)
    raise TimeoutError(f"Execution {run_id} did not finish within {timeout}s")


async def execute(client, request):
    accepted = await call(client, "submit_execution", {"request": request})
    completed = await wait_for_run(client, accepted["run_id"])
    if completed["status"] != "succeeded":
        raise RuntimeError(completed)
    return completed


def summarize(record):
    return {
        key: record[key]
        for key in (
            "run_id",
            "status",
            "execution_mode",
            "physical_execution",
            "completion_evidence",
        )
    }
