# Install SCP-Lab

[简体中文](zh-CN/installation.md) · [User guide](README.md) · [Home](../README.md)

Install SCP-Lab from source and prepare its local environment. Once installed, you can try the optional device-call and simulation tutorials, or proceed directly to agent and device integration.

## Prerequisites

- Git, if you clone the repository. You can also download and extract the full repository archive.
- [uv](https://docs.astral.sh/uv/getting-started/installation/), which manages Python, the virtual environment, and dependencies.
- Internet access for the initial dependency download. The commands below use Python 3.12; uv can download it if it is not already available.

The commands work in macOS/Linux terminals and Windows PowerShell. After installing Git and uv, open a new terminal and check:

```bash
git --version
uv --version
```

## 1. Get the source

Clone the repository into a local directory named `scp-lab`.

```bash
git clone https://github.com/InternRobotics/SCP-Lab.git scp-lab
cd scp-lab
```

If you already downloaded or cloned the repository, open a terminal in its root directory instead. This is the directory containing `pyproject.toml`, `uv.lock`, and `src/`. Run the remaining commands there.

## 2. Install dependencies

```bash
uv sync --frozen --python 3.12 --extra mcp
```

This creates `.venv` and installs SCP-Lab and the dependencies needed by its MCP interface and clients. `--frozen` uses the existing dependency lockfile. Create an environment on each computer rather than copying `.venv` between machines.

The guides use `uv run --no-sync` to run commands in this environment without synchronizing dependencies again. You do not need to activate `.venv` manually.

## 3. Verify the installation

```bash
uv run --no-sync scp-lab --help
```

The output lists commands including `serve`, `devices`, `device`, and `mcp-config`. This checks that the command-line entry point loads; it does not start an experiment.

## Optional dependencies

### OT-2 simulation

Install this environment when you want to run the [advanced OT-2 tutorial](ot2-examples.md) or use the `ot2-sim` backend. Keep the Opentrons dependencies in `.venv-sim`, separate from the main SCP-Lab environment. Run the following commands from the repository root.

macOS/Linux:

```bash
uv venv --python 3.12 .venv-sim
uv pip sync --python .venv-sim/bin/python requirements-simulation.lock
.venv-sim/bin/opentrons_simulate --version
```

Windows PowerShell:

```powershell
uv venv --python 3.12 .venv-sim
uv pip sync --python .venv-sim/Scripts/python.exe requirements-simulation.lock
.venv-sim/Scripts/opentrons_simulate.exe --version
```

The last command checks the installed simulator version. With the current lockfile, the expected output is:

```text
opentrons_simulate 8.8.2
```

To configure and run a simulation, continue with the [advanced tutorial](ot2-examples.md). When connecting an MCP client, generate its [client configuration](clients.md) after installation so it includes the simulator environment.

## Choose what to do next

| Goal | Guide |
| --- | --- |
| Learn the interaction with a demonstration call | [First device call](getting-started.md), an optional tutorial |
| Explore code generation and official simulation | [Advanced tutorial: OT-2 simulation](ot2-examples.md) |
| Connect an agent or application | [Application integration](clients.md) |
| Configure your own devices or develop execution backends | [Device integration and backend development](backends.md) |
| Modify SCP-Lab code and run tests | [Contributing](../CONTRIBUTING.md) |

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| `git` or `uv` is not found | Install the tool and reopen the terminal so its executable is on `PATH`. Git is only needed for cloning. |
| `pyproject.toml` is not found | Run the command from the repository root, not its parent directory or `src/`. |
| `mcp` cannot be imported | Run the installation command with `--extra mcp`, then use `uv run --no-sync` from the repository root. |
