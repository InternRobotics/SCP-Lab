import asyncio
import json
import os
import sys
from pathlib import Path

import pytest

from scp_lab.client_config import make_client_config


def test_missing_explicit_simulator_is_reported(tmp_path):
    (tmp_path / "pyproject.toml").touch()
    with pytest.raises(ValueError, match="Simulator Python does not exist"):
        make_client_config(tmp_path, tmp_path / "missing")


@pytest.mark.mcp
def test_generated_config_works_outside_repo(tmp_path, monkeypatch):
    pytest.importorskip("mcp")
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    root = Path(__file__).resolve().parents[1]
    config = make_client_config(root)["mcpServers"]["scp-lab"]
    assert config["command"] == sys.executable
    assert Path(config["env"]["SCP_LAB_RUN_DIR"]).is_absolute()
    config["env"]["SCP_LAB_RUN_DIR"] = str(tmp_path / "runs")
    # Test the generated config just as a desktop client starting from another cwd would use it.
    config["cwd"] = str(tmp_path)

    async def scenario():
        async with stdio_client(StdioServerParameters(**config)) as (read, write):
            async with ClientSession(read, write) as client:
                await client.initialize()
                request = json.loads((root / "examples/requests/liquid_transfer.json").read_text())
                result = await client.call_tool(request["name"], request["arguments"])
                assert not result.isError
                payload = result.structuredContent or json.loads(result.content[0].text)
                assert payload["validation"]["required_tips"] == 1
                if os.environ.get("SCP_LAB_SIM_PYTHON"):
                    request["arguments"]["mode"] = "simulate"
                    result = await client.call_tool(request["name"], request["arguments"])
                    assert not result.isError
                    payload = result.structuredContent or json.loads(result.content[0].text)
                    assert payload["status"] == "succeeded", payload

    asyncio.run(scenario())
