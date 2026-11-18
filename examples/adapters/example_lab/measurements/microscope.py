"""Acquire a JPEG snapshot from an OpenFlexure camera and return a local artifact."""

import hashlib
import tempfile
from functools import partial
from pathlib import Path

from pydantic import DirectoryPath, field_validator

from scp_lab.device_config import DeviceConfig
from scp_lab.execution_models import Contract

from ..http_api import ServiceConnection
from .backend import MeasurementBackend


class SnapshotOptions(Contract):
    output_dir: DirectoryPath

    @field_validator("output_dir")
    @classmethod
    def absolute_path(cls, path):
        if not path.is_absolute():
            raise ValueError("output_dir must be an existing absolute directory")
        return path


def take_snapshot(connection: ServiceConnection, output_dir: Path) -> dict:
    client = connection.open_connection()
    try:
        client.request("GET", "/camera/snapshot", headers={"Accept": "image/jpeg"})
        response = client.getresponse()
        if response.status != 200 or response.headers.get_content_type() != "image/jpeg":
            raise ValueError(f"Expected a JPEG from /camera/snapshot (HTTP {response.status})")
        limit = 16 * 1024 * 1024
        data = response.read(limit + 1)
        if len(data) > limit or not data.startswith(b"\xff\xd8") or not data.endswith(b"\xff\xd9"):
            raise ValueError("Invalid, oversized or incomplete JPEG snapshot")
    finally:
        client.close()

    image = tempfile.NamedTemporaryFile(
        dir=output_dir, prefix="snapshot-", suffix=".jpg", delete=False
    )
    path = Path(image.name)
    try:
        with image:
            image.write(data)
    except OSError:
        path.unlink(missing_ok=True)
        raise
    return {
        "uri": path.as_uri(),
        "byte_count": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def create_backend(config: DeviceConfig) -> MeasurementBackend:
    connection = ServiceConnection.model_validate(config.connection)
    options = SnapshotOptions.model_validate(config.options)
    return MeasurementBackend(
        config, "openflexure_microscope", partial(take_snapshot, connection, options.output_dir)
    )
