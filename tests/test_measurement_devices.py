import asyncio
import base64
import hashlib
import json
import struct
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from socketserver import StreamRequestHandler, TCPServer
from threading import Thread
from urllib.parse import unquote, urlparse

import pytest

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


@contextmanager
def serve(server_type, handler):
    with server_type(("127.0.0.1", 0), handler) as server:
        thread = Thread(target=server.serve_forever, kwargs={"poll_interval": 0.02})
        thread.start()
        try:
            yield server.server_address[1]
        finally:
            server.shutdown()
            thread.join()


@pytest.fixture
def acquire(tmp_path, monkeypatch):
    pytest.importorskip("mcp")
    monkeypatch.syspath_prepend(str(EXAMPLES))
    from device_client import call, connect, wait_for_run

    def run(model, operation, connection, **options):
        config = json.loads((EXAMPLES / "measurement-devices" / f"{model}.json").read_text())
        config["connection"].update(connection)
        config.setdefault("options", {}).update(options)
        (tmp_path / "device.json").write_text(json.dumps(config))

        async def scenario():
            async with connect(
                {"SCP_LAB_DEVICES_DIR": str(tmp_path), "PYTHONPATH": str(EXAMPLES / "adapters")}
            ) as client:
                descriptor = await call(client, "describe_device", {"device_id": model})
                assert descriptor["model_id"] == model
                cap = f"{model}.{operation}"
                assert [c["capability_id"] for c in descriptor["capabilities"]] == [cap]
                run = await call(
                    client,
                    "submit_execution",
                    {"request": {"device_id": model, "capability_id": cap, "arguments": {}}},
                )
                return await wait_for_run(client, run["run_id"])

        return asyncio.run(scenario())

    return run


@pytest.mark.parametrize(
    ("model", "query", "reply", "channel"),
    [
        ("stemlab_125_14", b"ANALOG:PIN? AIN0\r\n", b"2.125\r\n", "AIN0"),
        ("eez_bb3", b"MEAS:VOLT? CH1\r\n", b"2.125\n", "CH1"),
        ("eez_bb3", b"MEAS:VOLT? CH1\r\n", b"NaN\n", "CH1"),
    ],
)
def test_scpi(acquire, model, query, reply, channel):
    requests = []

    class Instrument(StreamRequestHandler):
        def handle(self):
            requests.append(self.rfile.readline())
            self.wfile.write(reply)

    with serve(TCPServer, Instrument) as port:
        record = acquire(model, "read_voltage", {"host": "127.0.0.1", "port": port})
    assert requests == [query]
    if reply.startswith(b"NaN"):
        assert record["status"] == "failed" and record["device_released"]
    else:
        assert record["status"] == "succeeded"
        assert record["result"] == {"channel": channel, "voltage_v": 2.125}


@pytest.mark.parametrize("success", [True, False])
def test_snapshot(acquire, tmp_path, success):
    jpeg = base64.b64decode(
        "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/wAALCAABAAEBAREA/8QAFAABAAAAAAAAAAAAAAAAAAAACP/EABQQAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQEAAD8AP7//2Q=="
    )
    paths = []

    class Camera(BaseHTTPRequestHandler):
        def do_GET(self):
            paths.append(self.path)
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.end_headers()
            self.wfile.write(jpeg if success else jpeg[:-4])

    with serve(HTTPServer, Camera) as port:
        record = acquire(
            "openflexure_microscope",
            "snapshot",
            {"base_url": f"http://127.0.0.1:{port}"},
            output_dir=str(tmp_path),
        )
    assert paths == ["/camera/snapshot"]
    if success:
        assert record["status"] == "succeeded"
        result = record["result"]
        assert Path(unquote(urlparse(result["uri"]).path)).read_bytes() == jpeg
        assert result["byte_count"] == len(jpeg)
        assert result["sha256"] == hashlib.sha256(jpeg).hexdigest()
    else:
        assert record["status"] == "failed" and record["device_released"]
        assert not list(tmp_path.glob("*.jpg"))


@pytest.mark.parametrize(
    ("model", "operation", "identifier", "function", "payload", "expected"),
    [
        ("load_cell_v2", "read_weight", 2104, 1, struct.pack("<i", -42), {"weight_g": -42}),
        ("co2_v2", "read_co2", 2147, 9, struct.pack("<H", 465), {"co2_ppm": 465}),
        (
            "color_v2",
            "read_color",
            2128,
            1,
            struct.pack("<4H", 120, 420, 210, 800),
            {"red": 120, "green": 420, "blue": 210, "clear": 800},
        ),
        (
            "humidity_v2",
            "read_humidity",
            283,
            1,
            struct.pack("<H", 4875),
            {"relative_humidity_percent": 48.75},
        ),
        ("humidity_v2", "read_humidity", 2104, 1, b"", None),
    ],
)
def test_bricklet_with_vendor_bindings(
    acquire, model, operation, identifier, function, payload, expected
):
    pytest.importorskip("tinkerforge")
    requests = []
    identity = struct.pack("<8s8sc3B3BH", b"2", b"3", b"a", 2, 0, 0, 2, 0, 0, identifier)

    class BrickDaemon(StreamRequestHandler):
        def handle(self):
            while header := self.rfile.read(8):
                uid, length, fid, seq, _ = struct.unpack("<IBBBB", header)
                self.rfile.read(length - 8)
                requests.append((uid, fid))
                data = identity if fid == 255 else payload
                self.wfile.write(
                    struct.pack("<IBBBB", uid, 8 + len(data), fid, seq & 0xF0, 0) + data
                )

    with serve(TCPServer, BrickDaemon) as port:
        record = acquire(model, operation, {"host": "127.0.0.1", "port": port, "uid": "2"})
    if expected is None:
        assert requests == [(1, 255)]
        assert record["status"] == "failed" and record["device_released"]
    else:
        assert requests == [(1, 255), (1, function)]
        assert record["status"] == "succeeded"
        assert record["result"] == expected
