# JSON Schemas

[简体中文](README.zh-CN.md) · [Documentation](../docs/README.md) · [Home](../README.md) · [Protocol reference](../docs/device-access.md)

## Common SCP-Lab device access schemas

| File | Object |
| --- | --- |
| [device-descriptor.schema.json](device-descriptor.schema.json) | Static identity, capabilities, schemas, and execution-mode declarations |
| [device-state.schema.json](device-state.schema.json) | Dynamic availability, occupancy, and optional observations |
| [execution-request.schema.json](execution-request.schema.json) | A request targeting one device capability |
| [execution-record.schema.json](execution-record.schema.json) | The request's status, effective arguments, result, errors, and evidence |

A capability's `input_schema` and `result_schema`, and a device's optional `state_schema`, describe its own fields. Retrieve them with `describe_device`; the common request schema does not prescribe all devices' experimental parameters.

The common schemas are also exposed as MCP resources under `scp-lab://schemas/device-descriptor`, `scp-lab://schemas/device-state`, `scp-lab://schemas/execution-request`, and `scp-lab://schemas/execution-record`.

## Reference-server deployment configuration

[device-config.schema.json](device-config.schema.json) defines one persistent device instance configuration. The backend validates its own `connection` and `options` fields. This is a local deployment format, separate from the SCP-Lab wire formats; other protocol implementations can use their own configuration storage. See [Device integration](../docs/backends.md).

## Adapter model definitions

[device-model.schema.json](device-model.schema.json) describes an independently stored model: `model_id`, `device_class`, `display_name`, `capabilities`, and optional `state_schema`. Each capability uses the common input/result schema structure. This is an adapter authoring format; clients obtain capabilities from `describe_device`, and adapters may also generate schemas in code.

The built-in definitions live in [adapters/<family>/models/](../src/scp_lab/adapters). An instance selects a file through the offline backend's `options.model_resource` or `options.model_file`. See [add a model](../docs/backends.md#add-a-model-for-offline-validation) for a complete example.

## OT-2-specific formats

| File | Scope |
| --- | --- |
| [protocol.schema.json](protocol.schema.json) | A multi-step experimental input for the OT-2 compiler |
| [ot2-capabilities.json](ot2-capabilities.json) | The implemented OT-2 compiler/simulator capability catalog |

Here, “protocol” means an experimental procedure for that backend. `protocol.schema.json` is not the universal input format for SCP-Lab devices. See the [OT-2 examples](../docs/ot2-examples.md).

Regenerate these files with `uv run --no-sync python scripts/export_schemas.py`; see [Contributing](../CONTRIBUTING.md).
