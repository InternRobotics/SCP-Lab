"""Generate local stdio configuration without changing any MCP application's settings."""

import os
import sys
from pathlib import Path

from .device_config import configured_directory


def make_client_config(
    project_dir: Path,
    simulator_python: Path | None = None,
    devices_dir: Path | None = None,
) -> dict:
    root = project_dir.expanduser().absolute()
    if not (root / "pyproject.toml").is_file():
        raise ValueError("Run mcp-config in the repository root or pass --project-dir")
    explicit_simulator = simulator_python or os.environ.get("SCP_LAB_SIM_PYTHON")
    candidate = (
        Path(explicit_simulator).expanduser().absolute()
        if explicit_simulator
        else root / ".venv-sim" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    )
    if explicit_simulator and not candidate.is_file():
        raise ValueError(f"Simulator Python does not exist: {candidate}")
    env = {"SCP_LAB_RUN_DIR": str(root / ".scp-lab" / "runs")}
    if candidate.is_file():
        env["SCP_LAB_SIM_PYTHON"] = str(candidate)
    selected = devices_dir if devices_dir is not None else os.environ.get("SCP_LAB_DEVICES_DIR")
    if selected is not None:
        env["SCP_LAB_DEVICES_DIR"] = str(configured_directory(selected))
    if os.environ.get("SCP_LAB_BACKEND_FACTORY"):
        raise ValueError("Replace SCP_LAB_BACKEND_FACTORY with device JSON files and --devices-dir")
    return {
        "mcpServers": {
            "scp-lab": {
                # Do not resolve symlinks: the virtualenv executable preserves its installed packages.
                "command": str(Path(sys.executable).absolute()),
                "args": ["-m", "scp_lab.server"],
                "env": env,
            }
        }
    }
