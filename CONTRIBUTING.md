# Contributing to SCP-Lab

[简体中文](CONTRIBUTING.zh-CN.md) · [Documentation](docs/README.md) · [Home](README.md) · [Protocol reference](docs/device-access.md) · [Device integration](docs/backends.md)

Contributions can improve protocol definitions, client examples, device adapters, or validation. For a device integration, start with the [backend template](examples/adapters/example_lab/plate_reader/backend.py) and describe the execution mode and evidence your adapter actually provides.

## Development environment

From the repository root:

```bash
uv sync --frozen --python 3.12 --extra mcp --extra dev
uv run --no-sync ruff check src tests examples scripts
uv run --no-sync ruff format --check src tests examples scripts
uv run --no-sync scp-lab check
uv run --no-sync pytest -q
```

To include official simulator tests, install the [OT-2 environment](docs/installation.md#ot-2-simulation) and set `SCP_LAB_SIM_PYTHON` before running pytest. Simulator tests are skipped when that optional environment is unavailable.

## Generated files

Public schemas are exported from the validation models. Regenerate them after changing models:

```bash
uv run --no-sync python scripts/export_schemas.py
```

### Device definitions

Keep each model definition with its adapter under [src/scp_lab/adapters/](src/scp_lab/adapters), grouped by device class. A model JSON declares its identity and capabilities, including input/result schemas and completion criteria. The offline backend loads one definition per instance and records its source and SHA-256 hash.

Default instance configurations live in `src/scp_lab/data/devices/`. To expose a model for offline validation, add a configuration using `scp_lab.adapters.offline:create_backend` and `options.model_resource` in `package:relative/path.json` form. Local integrations can instead specify an absolute `options.model_file`. Use one JSON configuration per instance; these files share the user-facing device loader.

Review model definitions directly and keep their units, bounds, and completion criteria consistent with the interface being described.

## Release layout

```bash
uv build
uv run --no-sync python scripts/check_release.py dist
```

The wheel includes the individual model files and default instance configurations. The source distribution also contains bilingual guides, examples, tests, and development scripts. The release check verifies these files and excludes import-only reference material and aggregate model data. New model definitions can follow the [offline integration tutorial](docs/backends.md#add-a-model-for-offline-validation); SDK adapters can follow the [reader package](examples/adapters).

## Changes to review together

For an interface change, include the relevant schema, behavior, and documentation. Keep examples runnable from the documented installation. For backends, identify what is checked by schema validation, SDK execution, simulation, or physical observations. Run checks appropriate to the changed behavior.

Device-specific inputs, results, and optional observations belong in that device's schemas. Changes to the common message structure should explain how existing clients and backends interpret them.

Guides are available in English and Simplified Chinese, with counterpart links at the top of each page. Update both versions when changing user-facing behavior or instructions; keep commands, field names, and expected results consistent.
