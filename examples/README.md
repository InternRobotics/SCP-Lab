# SCP-Lab examples

[简体中文](README.zh-CN.md) · [Documentation](../docs/README.md) · [Home](../README.md) · [Installation](../docs/installation.md) · [Client integration](../docs/clients.md) · [Device integration](../docs/backends.md)

Run these examples from the repository root after installation. They are ordinary Python MCP clients; no model API key is required. Each client starts its own local server and keeps a session open for submission and polling.

## Start with one call

```bash
uv run --no-sync python examples/quickstart.py
```

[quickstart.py](quickstart.py) discovers a demonstration heater, reads its capability, submits a request, and retrieves an execution record. Change `request.arguments` to try different values. The shared [device_client.py](device_client.py) handles the MCP connection and response envelope.

## Explore a specific use case

| Command | Expected behavior |
| --- | --- |
| `uv run --no-sync python examples/ot2_simulation.py` | Run a transfer through `ot2-sim`; requires the [optional simulator environment](../docs/ot2-examples.md) |
| `uv run --no-sync python examples/01_device_call.py` | Discover local instances and validate representative device requests |
| `uv run --no-sync python examples/02_multi_device.py` | Call liquid handling, incubation, and reading interfaces in a caller-defined sequence |
| `uv run --no-sync python examples/03_runtime.py` | Observe progress, reject a busy-device request, deduplicate a repeated request, cancel, and handle an injected failure |
| `uv run --no-sync python examples/04_custom_backend.py` | Load two reader configurations through one adapter, then invoke each with separate settings and observations |

`01_device_call.py --simulate` additionally invokes the OT-2 simulator after the catalog calls. Use [ot2_simulation.py](ot2_simulation.py) to run just that device example.

## Understand the feedback

- The catalog examples return `schema_validation` evidence. They validate input schemas without calling the corresponding SDKs.
- The multi-device example submits requests to transfer 50 uL, incubate at 37 °C for 30 minutes, and read absorbance, sharing the identifier `sample-plate` across requests. The caller defines the sequence; no automatic plate transfer or sample-location verification occurs.
- The heater examples use a software timer. They exercise execution behavior, not thermodynamics.
- The reader template in `adapters/example_lab/plate_reader/backend.py` returns `synthetic=true`. `04_custom_backend.py` loads the persistent JSON files in [devices/](devices) through that same adapter. Each reader has independent settings and an observation reporting `last_plate_id` with `kind="simulated"`, source, and timestamp. The client starts its own server; editing its Python calls changes the experiment, while editing the JSON files changes configured instances on the next startup.
- The OT-2 example returns `official_simulator_runlog` evidence and `physical_execution=false`.

See [devices and execution modes](../docs/devices.md) to interpret each kind of result.

## Request files and backend template

| File | Purpose |
| --- | --- |
| [requests/device_classes.json](requests/device_classes.json) | Complete representative device requests |
| [requests/ot2_execution.json](requests/ot2_execution.json) | Setup, initial liquids, and transfer arguments for `ot2-sim` |
| [adapters/](adapters) | Installable reader package with separate model JSON, schema loader, backend, and factory |
| [models/example_heater.json](models/example_heater.json) | Standalone model used in the [offline integration tutorial](../docs/backends.md#add-a-model-for-offline-validation) |
| [protocols/](protocols/) | Multi-step experimental inputs for the OT-2 compiler |

The `mcp_client.py` and `call_tool.py` scripts exercise OT-2-specific helper tools. See the [OT-2 guide](../docs/ot2-examples.md) for their formats. Task IDs from one example's server cannot be queried from a different server process.

The other examples use the bundled default device selection. If `SCP_LAB_DEVICES_DIR` selects a local directory, those examples require their referenced instance IDs to be present in that directory.
