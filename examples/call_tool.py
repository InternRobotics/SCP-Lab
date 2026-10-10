"""Call an MCP tool using generated local config and a complete request JSON."""

import argparse
import asyncio
import json
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def run(config_path: Path, request_path: Path):
    config = json.loads(config_path.read_text(encoding="utf-8"))["mcpServers"]["scp-lab"]
    request = json.loads(request_path.read_text(encoding="utf-8"))
    parameters = StdioServerParameters(**config)
    async with stdio_client(parameters) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(request["name"], request.get("arguments", {}))
            if result.isError:
                raise RuntimeError(result.content)
            payload = result.structuredContent or json.loads(result.content[0].text)
            print(json.dumps(payload, indent=2, ensure_ascii=False))
            if payload.get("ok") is False:
                raise RuntimeError(payload["error"])
            if payload.get("status") in ("failed", "unavailable"):
                raise RuntimeError(payload.get("error", "Requested operation did not succeed"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Call a local SCP-Lab MCP tool")
    parser.add_argument("request", type=Path)
    parser.add_argument("--config", type=Path, default=Path("mcp-config.json"))
    args = parser.parse_args()
    asyncio.run(run(args.config, args.request))
