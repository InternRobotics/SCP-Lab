"""Example: python examples/mcp_client.py examples/protocols/serial_dilution.json --simulate"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def run(path: Path, simulate: bool):
    env = {k: v for k, v in os.environ.items() if k in ("SCP_LAB_SIM_PYTHON", "SCP_LAB_RUN_DIR")}
    parameters = StdioServerParameters(
        command=sys.executable, args=["-m", "scp_lab.server"], env=env
    )
    async with stdio_client(parameters) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print("MCP tools:", ", ".join(t.name for t in tools.tools))
            protocol = json.loads(path.read_text(encoding="utf-8"))
            for name in ("validate_protocol", "compile_protocol") + (
                ("simulate_protocol",) if simulate else ()
            ):
                result = await session.call_tool(name, {"protocol": protocol})
                if result.isError:
                    raise RuntimeError(result.content)
                payload = result.structuredContent
                if payload is None:
                    payload = json.loads(result.content[0].text)
                if name == "simulate_protocol":
                    print(
                        json.dumps(
                            {
                                k: payload.get(k)
                                for k in (
                                    "run_id",
                                    "status",
                                    "command_count",
                                    "error",
                                    "completion_evidence",
                                )
                            },
                            indent=2,
                        )
                    )
                    if payload["status"] != "succeeded":
                        raise RuntimeError(payload.get("error", "Simulation did not succeed"))
                elif name == "compile_protocol":
                    print(payload["code"])
                else:
                    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("protocol", type=Path)
    parser.add_argument("--simulate", action="store_true")
    args = parser.parse_args()
    asyncio.run(run(args.protocol, args.simulate))
