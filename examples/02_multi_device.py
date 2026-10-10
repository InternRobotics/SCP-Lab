"""An explicit caller-authored sequence; device handoffs are declarations, not robot motion."""

import asyncio
import json

from device_client import ROOT, connect, execute


async def main():
    requests = json.loads((ROOT / "examples/requests/device_classes.json").read_text())
    by_device = {r["device_id"]: r for r in requests}
    sequence = [
        "hamilton_star-validation",
        "cytomat_6002-validation",
        "agilent_biotek_synergy_h1-validation",
    ]
    async with connect() as client:
        for device_id in sequence:
            result = await execute(client, by_device[device_id])
            print(
                json.dumps(
                    {
                        "device_id": device_id,
                        "status": result["status"],
                        "evidence": result["completion_evidence"]["kind"],
                        "command": result["result"]["validated_command"],
                    },
                    ensure_ascii=False,
                )
            )
    print(
        "Three requests passed schema validation. No plate was moved and no readings were measured."
    )


if __name__ == "__main__":
    asyncio.run(main())
