"""Invoke the optional OT-2 official simulator through the core MCP device interface."""

import asyncio
import json

from device_client import ROOT, call, connect, execute, summarize


async def main():
    request = json.loads((ROOT / "examples/requests/ot2_execution.json").read_text())
    async with connect() as client:
        state = await call(client, "get_device_state", {"device_id": request["device_id"]})
        if not state["available"]:
            raise RuntimeError(f"{state['availability_message']} See docs/ot2-examples.md.")
        descriptor = await call(client, "describe_device", {"device_id": request["device_id"]})
        request["expected_descriptor_revision"] = descriptor["descriptor_revision"]
        record = await execute(client, request)
        if record["completion_evidence"]["kind"] != "official_simulator_runlog":
            raise RuntimeError(record)
        print(json.dumps({**summarize(record), "simulation": record["result"]}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
