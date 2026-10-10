"""Observe progress, busy errors, duplicate submission, cancellation and an injected failure."""

import asyncio
import json

from device_client import call, connect, execute, summarize, wait_for_run


async def main():
    request = {
        "device_id": "demo-heater",
        "capability_id": "demo_heater.hold",
        "arguments": {"target_celsius": 37, "duration_s": 2},
        "idempotency_key": "demo-request-1",
    }
    async with connect() as client:
        first = await call(client, "submit_execution", {"request": request})
        duplicate = await call(client, "submit_execution", {"request": request})
        assert first["run_id"] == duplicate["run_id"]
        print("Duplicate request returned the same run ID:", first["run_id"])
        busy = await call(
            client,
            "submit_execution",
            {"request": {**request, "idempotency_key": "second"}},
            expected_error="device_busy",
        )
        print("Conflicting request:", busy["code"])
        state = await call(client, "get_device_state", {"device_id": "demo-heater"})
        assert state["state"] == "busy", state
        print("Device state:", state["state"])
        await asyncio.sleep(0.25)
        running = await call(client, "get_execution", {"run_id": first["run_id"]})
        print("Progress:", running["status"], running["progress"])
        cancellation = await call(client, "cancel_execution", {"run_id": first["run_id"]})
        print("Cancellation requested:", cancellation["status"])
        cancelled = await wait_for_run(client, first["run_id"])
        assert cancelled["status"] == "cancelled", cancelled
        print(json.dumps(summarize(cancelled)))
        success = await execute(
            client,
            {
                **request,
                "idempotency_key": "after-cancel",
                "arguments": {"target_celsius": 37, "duration_s": 0.1},
            },
        )
        print("Device reusable after confirmed mock stop:", success["status"])
        failure = await call(
            client,
            "submit_execution",
            {
                "request": {
                    **request,
                    "device_id": "demo-heater-fault",
                    "arguments": {"target_celsius": 37, "duration_s": 0.1},
                }
            },
        )
        failed = await wait_for_run(client, failure["run_id"])
        assert failed["status"] == "failed", failed
        print("Injected failure:", failed["error"])


if __name__ == "__main__":
    asyncio.run(main())
