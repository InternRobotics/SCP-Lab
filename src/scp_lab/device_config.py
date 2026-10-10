"""Persistent instance configuration for the reference server, separate from capabilities."""

import json
from importlib.resources import files
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, StrictBool, model_validator

from .execution_models import Contract


class DeviceConfig(Contract):
    schema_version: Literal["scp-lab.device-config.v0.1"] = "scp-lab.device-config.v0.1"
    device_id: str = Field(min_length=1)
    backend: str = Field(pattern=r"^[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*:[A-Za-z_]\w*$")
    display_name: str | None = None
    enabled: StrictBool = True
    connection: dict[str, Any] = Field(default_factory=dict)
    options: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def finite_json(self):
        json.dumps(self.model_dump(), allow_nan=False)
        return self


def configured_directory(value: str | Path) -> Path:
    if not str(value).strip():
        raise ValueError("Device configuration directory must not be empty")
    path = Path(value).expanduser().absolute()
    if not path.is_dir():
        raise ValueError(f"Device configuration directory does not exist: {path}")
    return path


def _unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def load_device_configs(directory: str | Path | None = None) -> list[tuple[str, DeviceConfig]]:
    """Read every JSON file once. An explicit directory replaces the bundled selection."""
    source = (
        configured_directory(directory)
        if directory is not None
        else files("scp_lab").joinpath("data/devices")
    )
    configs = []
    identifiers = {}
    for path in sorted(source.iterdir(), key=lambda item: item.name):
        if not path.is_file() or not path.name.endswith(".json"):
            continue
        try:
            value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_keys)
            config = DeviceConfig.model_validate(value)
        except (ValueError, OSError) as error:
            raise ValueError(f"Invalid device configuration {path}: {error}") from error
        if config.device_id in identifiers:
            raise ValueError(
                f"Duplicate device_id {config.device_id!r} in {path} and "
                f"{identifiers[config.device_id]}"
            )
        identifiers[config.device_id] = str(path)
        configs.append((str(path), config))
    return configs
