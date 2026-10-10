# Add an offline model definition

[简体中文](zh-CN/models.md) · [User guide](README.md) · [Device integration](backends.md) · [Home](../README.md)

Publish a discoverable, validated interface using a model definition and an instance configuration. Complete the [base installation](installation.md) first. Run the commands below from the repository root.

## Add a model for offline validation

Create `lab-models/` and `lab-devices/` directories for the model and instance files, then load the model through the existing offline backend. Start from one of the [45 model definitions](../src/scp_lab/adapters), or save [example_heater.json](../examples/models/example_heater.json) as `lab-models/example_heater.json` outside the device configuration directory.

The example publishes `example_heater.hold`. Its definition contains:

```json
{
  "schema_version": "scp-lab.device-model.v0.1",
  "model_id": "example_heater",
  "device_class": "temperature_controller",
  "display_name": "Example heater interface",
  "capabilities": [
    {
      "capability_id": "example_heater.hold",
      "description": "Validate a requested temperature and duration.",
      "input_schema": {
        "type": "object",
        "properties": {
          "target_celsius": {"type": "number", "minimum": 20, "maximum": 95, "x-scp-unit": "degC"},
          "duration_s": {"type": "number", "exclusiveMinimum": 0, "x-scp-unit": "s"}
        },
        "required": ["target_celsius", "duration_s"],
        "additionalProperties": false
      },
      "result_schema": {
        "type": "object",
        "required": ["validated_command", "source", "limitations"],
        "properties": {
          "validated_command": {"type": "object"},
          "source": {"type": "object"},
          "limitations": {"type": "array", "items": {"type": "string"}}
        }
      },
      "completion_criteria": "The declared parameter schema accepts the request.",
      "access_level": "L3"
    }
  ]
}
```

These illustrative limits define an offline example. Set parameter names, ranges, units, and required fields from the interface being integrated. Capabilities can have different argument structures; `parameters` and `bindings` are not mandatory wrappers. The [model-file schema](../schemas/device-model.schema.json) documents the outer format. Each entry in `capabilities` uses the same `Capability` structure published through `describe_device`.

Save a separate instance configuration as `lab-devices/heater-01.json`. Replace the absolute path below with the location of the saved model file:

```json
{
  "device_id": "heater-01",
  "backend": "scp_lab.adapters.offline:create_backend",
  "options": {"model_file": "/absolute/path/to/lab-models/example_heater.json"}
}
```

This example saves the capability definition locally in `lab-models/`, so `model_file` tells the backend which file to read. Use its absolute path on the machine running the SCP-Lab server. For definitions installed with a Python package, use `model_resource` instead. See [capability-definition file locations](backends.md#model-definition-location) for how to choose between the two methods.

Every JSON file in the selected instance directory is treated as an instance configuration, so keep capability definitions in `lab-models/` and instance configurations in `lab-devices/`.

Inspect the configured interface and generate the client configuration:

```bash
uv run --no-sync scp-lab device heater-01 --devices-dir ./lab-devices
uv run --no-sync scp-lab check --devices-dir ./lab-devices
uv run --no-sync scp-lab mcp-config --devices-dir ./lab-devices --output mcp-config.json
```

Apply that configuration using the [application guide](clients.md), restart the server, then submit:

```json
{
  "request": {
    "device_id": "heater-01",
    "capability_id": "example_heater.hold",
    "arguments": {"target_celsius": 37, "duration_s": 60}
  }
}
```

The task validates these values and returns immediately; it does not wait 60 seconds or heat anything. The offline backend returns `validated_command`, `source`, and `limitations`, so its model files declare that report's result schema and completion criteria. It uses `defaults_policy="not_applied"`. An interface that resolves defaults, reports different results, or needs additional checks can supply its own backend.

To contribute a bundled model, place it in `src/scp_lab/adapters/<family>/models/<model_id>.json`, add an instance configuration referencing its package resource, and include a representative request. For a new family, add an `__init__.py` so its files form an importable package. Run `scp-lab check` and exercise the request.

## How the files fit together

The [built-in adapters](../src/scp_lab/adapters) are organized by device family. Each model is maintained in its own file.

```text
src/scp_lab/
├── backend.py                     # Common backend interface and schema validation
├── adapters/
│   ├── schemas.py                 # Read and validate one model definition
│   ├── offline.py                 # Reusable offline validation backend and factory
│   ├── plate_reader/models/
│   │   ├── agilent_biotek_synergy_h1.json
│   │   └── ...
│   ├── liquid/
│   │   ├── models/ot2.json         # Offline OT-2 interface
│   │   ├── ot2_schemas.py          # Compiler/simulator capability schemas
│   │   └── ot2.py                 # Official simulation backend and factory
│   └── heater/
│       ├── models/demo_heater.json
│       ├── schemas.py
│       └── backend.py
└── data/devices/                   # One saved configuration per instance
```

The 45 offline models use the same backend with their own schemas. A family can add its own `schemas.py` or `backend.py` when it needs schema generation, additional checks, or SDK behavior. Those modules can also live in a separately installed adapter package. Declarative models reuse the offline factory and define their capabilities in separate JSON files.
