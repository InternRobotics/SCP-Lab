# Device models and adapters

[简体中文](README.zh-CN.md) · [Home](../../../README.md) · [Device integration](../../../docs/backends.md)

The 45 offline device models are maintained as individual JSON files in `<family>/models/`. These files contain native SCP-Lab capability definitions and are included directly in the installed package. They are both callable interfaces for applications and starting points for new device integrations.

| Part | Responsibility |
| --- | --- |
| `<family>/models/<model_id>.json` | Model identity, capabilities, input/result schemas, and completion criteria |
| [schemas.py](schemas.py) | Load and validate one model file from a package resource or absolute local path |
| [offline.py](offline.py) | Shared offline validation implementation and factory |
| [liquid/ot2.py](liquid/ot2.py) and [ot2_schemas.py](liquid/ot2_schemas.py) | OT-2 compilation, official simulation, and generated capability schemas |
| [heater/](heater) | A model file, schema loader, and timed demonstration backend |
| [../data/devices/](../data/devices) | Independent configurations selecting a backend and model for each instance |

For example, [the Synergy H1 model](plate_reader/models/agilent_biotek_synergy_h1.json) declares its capabilities, while [its default instance](../data/devices/agilent_biotek_synergy_h1-validation.json) selects the offline factory and points directly to that model resource. Several instances can select the same model file. No aggregate JSON, global model index, or generated catalog is required.

Add a model to an existing family without changing its Python code. Add a family as a Python package with an `__init__.py` and model files. A family needs its own behavior module only when it implements additional checks, simulation, or SDK calls. External adapters can use the same arrangement in separately installed packages.

Follow [the complete device tutorial](../../../docs/backends.md) to register an instance, add a local model, or develop an adapter. The [reader example package](../../../examples/adapters) includes separate model definitions, behavior, and schema loading. Parameter names, units, defaults, and completion criteria are explained in the [protocol reference](../../../docs/device-access.md).
