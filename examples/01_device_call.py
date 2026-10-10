"""Discover and invoke device interfaces; optionally call the official OT-2 simulator."""

import argparse
import asyncio
import json

from device_client import ROOT, call, connect, execute, summarize


async def main(simulate):
    requests = json.loads((ROOT / "examples/requests/device_classes.json").read_text())
    async with connect() as client:
        devices = await call(client, "list_devices")
        print(f"Discovered {len(devices)} local instances")
        for request in requests:
            description = await call(client, "describe_device", {"device_id": request["device_id"]})
            assert request["capability_id"] in {
                c["capability_id"] for c in description["capabilities"]
            }
            record = await execute(client, request)
            print(request["capability_id"], json.dumps(summarize(record)))
            assert record["completion_evidence"]["kind"] == "schema_validation"
        if simulate:
            request = json.loads((ROOT / "examples/requests/ot2_execution.json").read_text())
            record = await execute(client, request)
            print("OT-2", json.dumps(summarize(record)))
            assert record["completion_evidence"]["kind"] == "official_simulator_runlog"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--simulate", action="store_true")
    asyncio.run(main(parser.parse_args().simulate))
