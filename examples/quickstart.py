"""Discover a capability, submit one request, and read its execution record over MCP."""

import asyncio
import json

from device_client import call, connect, wait_for_run


async def main():
    # The helper starts a local MCP server and keeps one session open for the entire call.
    async with connect() as client:
        devices = await call(client, "list_devices", {"device_class": "temperature_controller"})
        device = next(item for item in devices if item["device_id"] == "demo-heater")
        print(f"list_devices -> {device['device_id']} ({device['execution_mode']})", flush=True)
        descriptor = await call(client, "describe_device", {"device_id": device["device_id"]})
        capability = next(
            item
            for item in descriptor["capabilities"]
            if item["capability_id"] == "demo_heater.hold"
        )
        print(f"describe_device -> {capability['capability_id']}", flush=True)

        # Change these values to try another call. Units and bounds come from input_schema.
        request = {
            "device_id": device["device_id"],
            "capability_id": capability["capability_id"],
            "arguments": {"target_celsius": 37, "duration_s": 1},
            "expected_descriptor_revision": descriptor["descriptor_revision"],
        }
        accepted = await call(client, "submit_execution", {"request": request})
        print(
            f"submit_execution -> {accepted['status']} (run_id={accepted['run_id']})",
            flush=True,
        )
        print("Polling get_execution every 0.2 s; showing status changes.", flush=True)
        record = await wait_for_run(client, accepted["run_id"], show_status=True)
        if record["status"] != "succeeded":
            raise RuntimeError(record)
        print("Result:", flush=True)
        print(
            json.dumps(
                {
                    "status": record["status"],
                    "execution_mode": record["execution_mode"],
                    "physical_execution": record["physical_execution"],
                    "evidence": record["completion_evidence"]["kind"],
                    "result": record["result"],
                },
                indent=2,
            )
        )
        state = await call(client, "get_device_state", {"device_id": device["device_id"]})
        print(f"get_device_state -> {state['state']}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
