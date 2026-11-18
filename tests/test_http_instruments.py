import asyncio
import json
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread

import pytest

from scp_lab.execution_models import ExecutionRequest, ProtocolError
from scp_lab.registry import create_runtime

ADAPTERS = Path(__file__).resolve().parents[1] / "examples" / "adapters"


@pytest.fixture
def instruments(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(ADAPTERS))
    replies = []
    calls = []

    class Instrument(BaseHTTPRequestHandler):
        def respond(self):
            raw = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            calls.append((self.command, self.path, self.headers, json.loads(raw) if raw else None))
            code, value = replies.pop(0)
            self.send_response(code)
            self.end_headers()
            self.wfile.write(json.dumps(value).encode())

        do_GET = do_POST = respond

    server = HTTPServer(("127.0.0.1", 0), Instrument)
    thread = Thread(target=server.serve_forever, kwargs={"poll_interval": 0.02})
    thread.start()
    try:
        origin = f"http://127.0.0.1:{server.server_port}"
        key = tmp_path / "key"
        key.write_text("fixture-key\n")
        for device in ("opentrons", "bioyond"):
            connection = {"base_url": origin}
            if device == "bioyond":
                connection["api_key_file"] = str(key)
            (tmp_path / f"{device}.json").write_text(
                json.dumps(
                    {
                        "device_id": device,
                        "backend": f"example_lab.{device}.backend:create_backend",
                        "connection": connection,
                    }
                )
            )
        runtime = create_runtime(tmp_path)
        assert not calls

        def invoke(capability, **arguments):
            async def run():
                request = ExecutionRequest(
                    device_id=capability.split(".")[0],
                    capability_id=capability,
                    arguments=arguments,
                )
                record = await runtime.submit(request)
                await runtime.tasks[record["run_id"]]
                return runtime.get_execution(record["run_id"])

            return asyncio.run(run())

        yield invoke, replies, calls
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


def test_rail_lights_wire_protocol(instruments):
    invoke, replies, calls = instruments
    with pytest.raises(ProtocolError):
        invoke("opentrons.set_rail_lights", on="false")
    assert calls == []
    replies.extend([(200, {"on": True}), (200, {"on": False}), (200, {"on": False})])
    read = invoke("opentrons.get_rail_lights")
    assert read["result"] == {"on": True}
    write = invoke("opentrons.set_rail_lights", on=False)
    assert write["status"] == "succeeded" and write["device_released"]
    assert write["result"] == {"on": False}
    assert write["completion_evidence"]["physical_completion_verified"] is False
    assert [(m, body) for m, _, _, body in calls] == [
        ("GET", None),
        ("POST", {"on": False}),
        ("GET", None),
    ]
    assert all(
        path == "/robot/lights" and headers["Opentrons-Version"] == "2"
        for _, path, headers, _ in calls
    )


@pytest.mark.parametrize(
    ("reply", "status", "released"),
    [
        ((200, {"on": False}), "failed", True),
        ((200, {"on": 1}), "unknown", False),
        ((503, {}), "unknown", False),
    ],
)
def test_write_requires_independent_readback(instruments, reply, status, released):
    invoke, replies, _ = instruments
    replies.extend([(200, {"on": True}), reply])
    write = invoke("opentrons.set_rail_lights", on=True)
    assert write["status"] == status
    assert write["device_released"] is released


def test_scheduler_status_wire_protocol(instruments):
    invoke, replies, calls = instruments
    replies.append((200, {"code": 1, "data": {"schedulerStatus": "Stop"}}))
    record = invoke("bioyond.get_scheduler_status")
    assert record["status"] == "succeeded" and record["device_released"]
    assert record["result"] == {"schedulerStatus": "Stop"}
    method, path, headers, payload = calls[0]
    assert (method, path) == ("POST", "/api/lims/scheduler/scheduler-status")
    assert headers["Content-Type"] == "application/json"
    assert payload["apiKey"] == "fixture-key"
    datetime.strptime(payload["requestTime"], "%Y-%m-%dT%H:%M:%S.%fZ")
    assert "fixture-key" not in json.dumps(record)


@pytest.mark.parametrize("reply", [(403, {}), (200, {"code": 0}), (200, {"code": 1, "data": {}})])
def test_scheduler_rejects_invalid_feedback(instruments, reply):
    invoke, replies, _ = instruments
    replies.append(reply)
    record = invoke("bioyond.get_scheduler_status")
    assert record["status"] == "failed" and record["device_released"]
    assert record["result"] == {}
