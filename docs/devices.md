# Devices and execution modes

[简体中文](zh-CN/devices.md) · [Documentation](README.md) · [Home](../README.md) · [First device call](getting-started.md) · [Connect your devices](backends.md)

Use this guide to choose an example or inspect an available interface. A **model** identifies a kind of instrument; an **instance** identifies one configured backend in your local server. Different instances of the same model can expose different capabilities.

## Choose an execution backend

Choose an instance by the work you want to check. Its `execution_mode` and completion evidence tell you how to interpret the result.

| Instance | Execution mode | What a successful call establishes |
| --- | --- | --- |
| `demo-heater`, `demo-heater-fault` | `mock` | A software demonstration completed, or reported its configured cancellation/failure |
| `ot2-sim` | `official_simulation` | Generated code completed in the optional Opentrons simulator |
| Instances ending in `-validation` | `schema_validation` | The request matches the published parameter and resource-binding schemas |
| `reader-01`, `reader-02`, loaded by the custom backend example | `mock` | A demonstration SDK returned explicitly synthetic readings |
| Your registered instance | Declared by your backend | The conditions and evidence published by your integration |

The default server loads [48 per-device JSON configurations](../src/scp_lab/data/devices) through the same loader used for local devices: 45 schema-validation instances, the OT-2 simulator, and two demonstration heaters. The simulator reports unavailable until its environment is configured. Bundled backends do not connect to physical equipment. Selecting a directory with `--devices-dir` or `SCP_LAB_DEVICES_DIR` replaces this default selection; adding an instance requires a new JSON file, not a change to the model catalog.

## Inspect and invoke an interface

```bash
uv run --no-sync scp-lab devices
uv run --no-sync scp-lab device agilent_biotek_synergy_h1-validation
uv run --no-sync python examples/01_device_call.py
```

The last command uses MCP to submit representative requests for a selection of bundled device models. Find the request payloads in [device_classes.json](../examples/requests/device_classes.json).

In your application, use `list_devices` and `describe_device` instead of assuming that a model name implies an installed driver. A static descriptor contains the actual capabilities and schemas published by that instance; availability is in its dynamic state.

## Interface catalog

The catalog includes 45 models and 89 capability definitions:

| Class | Model count |
| --- | ---: |
| Plate reader | 12 |
| Storage / incubator | 8 |
| Liquid handler | 6 |
| Heater-shaker | 5 |
| Thermocycler | 3 |
| Centrifuge | 2 |
| Plate sealer / unsealer | 2 |
| Temperature controller | 2 |
| Colony picker | 1 |
| Glovebox | 1 |
| Plate washer | 1 |
| Reagent dispenser | 1 |
| Tilter | 1 |

The offline validation backend publishes each interface's parameter names, ranges, enums, and conditional requirements. Use it to develop capability discovery and request construction before adding hardware access. Resource bindings are caller-supplied references checked for structure; physical sample locations and measurements require device feedback.

Model definitions live under [adapters/](../src/scp_lab/adapters), grouped by device class. The offline backend loads the model resource or local file named in its instance configuration and records the definition's source and SHA-256 hash.

## OT-2 simulation

[Install and run the OT-2 simulator](ot2-examples.md) for an example that generates and executes device code. `ot2-sim` exposes nine implemented capabilities. `ot2-validation` separately publishes ten capability definitions with different schemas. Describe the instance you intend to call rather than transferring arguments between them by name.

## Add your own device

Follow [Connect your devices](backends.md) to wrap an SDK, simulator, or existing laboratory service. A custom backend can publish additional capabilities or a new device class while using the same discovery, submission, and feedback tools.
