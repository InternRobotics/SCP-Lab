"""Load trusted local instance configurations; MCP callers cannot select Python code."""

import importlib
import os
from pathlib import Path

from .backend import DeviceBackend
from .device_config import load_device_configs
from .runtime import LocalExecutionRuntime


def create_runtime(devices_dir: str | Path | None = None) -> LocalExecutionRuntime:
    if os.environ.get("SCP_LAB_BACKEND_FACTORY"):
        raise ValueError(
            "SCP_LAB_BACKEND_FACTORY has been replaced by per-device JSON files. "
            "Remove that setting and select a directory with SCP_LAB_DEVICES_DIR; "
            "see docs/backends.md."
        )
    selected = devices_dir if devices_dir is not None else os.environ.get("SCP_LAB_DEVICES_DIR")
    # Validate all files and duplicate IDs before constructing any backend.
    configs = load_device_configs(selected)
    backends = []
    for source, config in configs:
        if not config.enabled:
            continue
        module, function = config.backend.split(":")
        try:
            factory = getattr(importlib.import_module(module), function)
            backend = factory(config.model_copy(deep=True))
            if not isinstance(backend, DeviceBackend):
                raise ValueError("Factory must return one DeviceBackend")
            if backend.description.device_id != config.device_id:
                raise ValueError("Backend device_id must match its instance configuration")
            if config.display_name is not None:
                backend.description = backend.description.model_copy(
                    update={"display_name": config.display_name}
                )
        except Exception as error:
            raise ValueError(
                f"Cannot load device {config.device_id!r} from {source}: {error}"
            ) from error
        backends.append(backend)
    return LocalExecutionRuntime(backends)
