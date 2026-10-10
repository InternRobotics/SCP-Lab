"""Load two independently configured readers using the same adapter."""

import asyncio
import json

from device_client import ROOT, call, connect, execute, summarize


async def main():
    # Only this source-tree demonstration needs PYTHONPATH. Installed adapters
    # are imported directly by the factory paths stored in device JSON files.
    async with connect(
        {
            "SCP_LAB_DEVICES_DIR": str(ROOT / "examples" / "devices"),
            "PYTHONPATH": str(ROOT / "examples" / "adapters"),
        }
    ) as client:
        devices = await call(client, "list_devices")
        assert {item["device_id"] for item in devices} == {"reader-01", "reader-02"}
        results = []
        for device in devices:
            device_id = device["device_id"]
            description = await call(client, "describe_device", {"device_id": device_id})
            record = await execute(
                client,
                {
                    "device_id": device_id,
                    "capability_id": "example_reader.read_absorbance",
                    "arguments": {"plate_id": f"plate-for-{device_id}", "wavelength_nm": 600},
                    "expected_descriptor_revision": description["descriptor_revision"],
                },
            )
            assert record["result"]["synthetic"] is True
            state = await call(client, "get_device_state", {"device_id": device_id})
            assert state["observation"]["values"]["last_plate_id"] == f"plate-for-{device_id}"
            results.append(
                {"device_id": device_id, **summarize(record), "result": record["result"]}
            )
        assert results[0]["result"]["values"] != results[1]["result"]["values"]
        print(json.dumps(results, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
