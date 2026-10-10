# Connect devices and develop backends

[简体中文](zh-CN/backends.md) · [User guide](README.md) · [Home](../README.md) · [Application integration](clients.md)

Use this guide to make device capabilities callable by an agent or application. An integration describes the available operations, how to execute them, and which local configuration to use:

| Part | What you provide | Plate-reader example |
| --- | --- | --- |
| Capability definitions | Operation names, input fields, result formats, and completion conditions | Plate ID, wavelength, and result format for an absorbance reading |
| Execution backend | Code that checks requests or calls an SDK, simulator, or control service | Check reading parameters or pass the reading request to the reader SDK |
| Instance configuration | One device's ID, backend, and connection settings | Which backend and instrument `reader-01` uses |

Capability definitions can be stored separately in JSON files, which the backend loads and supplies for SCP-Lab to register. Callers use `describe_device` to read the capability definitions and the execution mode (`execution_mode`) declared by the backend.

Complete the [base installation](installation.md), then choose a starting point:

| Starting point | Follow this path |
| --- | --- |
| Inspect registered model interfaces and configurations | [Browse bundled integration examples](#bundled-models-as-integration-examples) |
| Use an existing device interface | [Configure instances](#configure-devices-with-an-existing-backend) |
| Publish a new interface for offline validation | [Add a model definition](#add-a-model-for-offline-validation) |
| Connect a simulator, SDK, or laboratory service | [Develop an adapter](#develop-an-adapter-for-a-new-sdk-or-api) |

## Configure devices with an existing backend

This section uses a Synergy H1 plate reader to demonstrate configuring a device instance, querying its capabilities, and submitting a reading request. The example backend runs in `schema_validation` mode; it currently validates parameters and sample bindings and returns a validation report.

### 1. Save an instance configuration

For this example, create `lab-devices/` in the project root, the directory containing `pyproject.toml`:

```bash
mkdir -p lab-devices
```

You can keep the configuration directory elsewhere; use that path with `--devices-dir` in the following commands.

Save the following as `lab-devices/reader-01.json`:

```json
{
  "schema_version": "scp-lab.device-config.v0.1",
  "device_id": "reader-01",
  "display_name": "Reader 01 - offline interface validation",
  "backend": "scp_lab.adapters.offline:create_backend",
  "enabled": true,
  "connection": {},
  "options": {
    "model_resource": "scp_lab.adapters.plate_reader:models/agilent_biotek_synergy_h1.json"
  }
}
```

The configuration specifies three key items:

| Setting | Meaning in this example |
| --- | --- |
| `device_id` | A nonempty string chosen by the integrator for use in calls; `reader-01` is an example. IDs must be unique across the instance configurations loaded by the same server |
| `backend` | Use the bundled offline backend to check request formats |
| `options.model_resource` | Load the [Synergy H1 capability definition](../src/scp_lab/adapters/plate_reader/models/agilent_biotek_synergy_h1.json) |

<a id="how-a-backend-factory-works"></a>
The `backend` format is `Python module:function in that module that creates the backend`.

This example's `scp_lab.adapters.offline:create_backend` corresponds to:

```python
from scp_lab.adapters.offline import create_backend

backend = create_backend(config)
```

At startup, the server parses each enabled instance configuration into a `DeviceConfig` and passes it to the specified factory. The returned backend instance handles subsequent requests for that device.

<a id="model-definition-location"></a>
The `models/` directory stores capability-definition JSON files by device model, describing the operations offered, input and result schemas, and completion conditions. The bundled offline backend uses the following settings to locate the file to read:

| Setting | File location | When to use it |
| --- | --- | --- |
| `options.model_resource` | Inside an installed Python package, in the format `package:relative/path.json` | Use bundled definitions or distribute definitions with your own Python package |
| `options.model_file` | On the machine running the SCP-Lab server, specified by an absolute path | Load your own JSON file directly, without packaging and installing it first |

This example uses `model_resource`: `scp_lab.adapters.plate_reader` before the colon is the Python package name, and `models/agilent_biotek_synergy_h1.json` after it is the path within that package.

The bundled offline backend reads one capability definition per instance; choose either `model_resource` or `model_file`. To switch to a local file, replace `model_resource` in `options` with `model_file`.

Devices of the same model that provide the same interface and execution mode can share capability definitions and backend code. Save a separate instance configuration with a different `device_id`, such as `reader-02`. At startup, the server creates a separate backend object from each configuration. The offline backend in this example needs no connection information, so `connection` stays `{}`; for hardware, enter the corresponding device's connection information in each configuration.

### 2. Check the configured devices

From the repository root:

```bash
# List the devices in the selected directory.
uv run --no-sync scp-lab devices --devices-dir ./lab-devices
# Read reader-01's capabilities and input/result schemas.
uv run --no-sync scp-lab device reader-01 --devices-dir ./lab-devices
# Check descriptor and state formats.
uv run --no-sync scp-lab check --devices-dir ./lab-devices
```

The device list should contain `reader-01` with execution mode `schema_validation`. The `device` command's `capabilities` includes `agilent_biotek_synergy_h1.plate_reading`.

Excerpt from a successful `check` output:

```json
{
  "status": "passed",
  "execution_performed": false
}
```

This confirms that descriptor and state formats passed validation; no device operation was performed.

With `--devices-dir`, the server loads only that directory's top-level `*.json` files, replacing the default selection. This example directory contains only `reader-01`, so only that device is listed. To retain bundled examples, copy their configurations from [data/devices](../src/scp_lab/data/devices) into this directory. Restart the server after changing configurations or model definitions.

### 3. Connect and call it

```bash
uv run --no-sync scp-lab mcp-config --devices-dir ./lab-devices --output mcp-config.json
```

The generated configuration uses `SCP_LAB_DEVICES_DIR` to select the device directory. Follow the [application guide](clients.md) to merge the client configuration and restart the server, then query `reader-01` through `list_devices`.

Query the device descriptor to obtain the reading capability's `input_schema`:

```python
from examples.device_client import call

descriptor = await call(client, "describe_device", {"device_id": "reader-01"})
capability = next(
    item for item in descriptor["capabilities"]
    if item["capability_id"] == "agilent_biotek_synergy_h1.plate_reading"
)
input_schema = capability["input_schema"]
print(list(input_schema["properties"]["parameters"]["properties"]))
print(input_schema["properties"]["bindings"]["required"])
```

The output lists operation parameter fields and the required sample binding:

```text
['mode', 'wavelength', 'excitation_wavelength', 'emission_wavelength', 'focal_height']
['sample']
```

The request specifies an absorbance reading of the sample plate at 600 nm. Set `mode="absorbance"` and `wavelength=600`, then identify the plate through `bindings.sample.resource_id`:

```python
accepted = await call(client, "submit_execution", {
    "request": {
        "device_id": "reader-01",
        "capability_id": capability["capability_id"],
        "arguments": {
            "parameters": {"mode": "absorbance", "wavelength": 600},
            "bindings": {"sample": {"resource_id": "sample-plate"}}
        }
    }
})
```

Query the execution record with the returned task ID until execution ends:

```python
record = await call(client, "get_execution", {"run_id": accepted["run_id"]})
```

Excerpt from a successful record:

```json
{
  "status": "succeeded",
  "execution_mode": "schema_validation",
  "completion_evidence": {"kind": "schema_validation"},
  "result": {
    "validated_command": {
      "capability_id": "agilent_biotek_synergy_h1.plate_reading",
      "parameters": {"mode": "absorbance", "wavelength": 600},
      "bindings": {"sample": {"resource_id": "sample-plate"}}
    }
  }
}
```

Success here means the parameters and sample binding conform to the published schema. The `validated_command` contains the checked request, and `result.source` identifies the model file and its hash. This backend returns a validation report rather than physical absorbance readings.

See the [application guide](clients.md#2-discover-and-call-a-capability) and its linked example source for complete connection, polling, and outcome handling.

## Add a model for offline validation

If existing model definitions do not include the required operation, write a capability JSON file and check requests with the same offline backend. During development, use `model_file` to load a local file directly, specifying its absolute path in the instance configuration. See the [model-definition guide](models.md) for a complete definition, configuration, and call example.

<a id="bundled-models-as-integration-examples"></a>
## Use bundled models and configurations as examples

The project includes interface definitions for 45 models, providing 89 capabilities. Each model has an offline instance configuration. Use these files as examples of operation boundaries, input fields, resource bindings, and model/backend selection. These three models also provide the interfaces used in the [multi-device call example](../examples/02_multi_device.py):

| Model | Capability definition | Instance configuration |
| --- | --- | --- |
| Hamilton STAR liquid handler | [hamilton_star.json](../src/scp_lab/adapters/liquid/models/hamilton_star.json) | [hamilton_star-validation.json](../src/scp_lab/data/devices/hamilton_star-validation.json) |
| Cytomat 6002 incubator | [cytomat_6002.json](../src/scp_lab/adapters/storage/models/cytomat_6002.json) | [cytomat_6002-validation.json](../src/scp_lab/data/devices/cytomat_6002-validation.json) |
| Synergy H1 plate reader | [agilent_biotek_synergy_h1.json](../src/scp_lab/adapters/plate_reader/models/agilent_biotek_synergy_h1.json) | [agilent_biotek_synergy_h1-validation.json](../src/scp_lab/data/devices/agilent_biotek_synergy_h1-validation.json) |

These instances check requests in `schema_validation` mode. Their `result_schema` and `completion_criteria` describe the validation report and successful validation conditions, respectively. They do not connect to those models' SDKs or hardware.

For a hardware integration, use the file structure as a reference and check operations, parameter ranges, units, and sample positions against your SDK and device configuration. Define the actual result fields and completion conditions, then implement the execution backend as described in the next section. Some bundled fields still have ambiguous unit conventions; see the [device catalog](devices.md#interface-catalog).

The default server already registers these offline instances, so they can be queried directly through `list_devices` and `describe_device`. See [testing an agent with bundled interfaces](clients.md#bundled-device-interface-environment) for the call flow and agent-testing uses.

## Develop an adapter for a new SDK or API

### 1. Inspect the complete adapter example

[examples/04_custom_backend.py](../examples/04_custom_backend.py) loads two readers through one adapter and reads absorbance from each. Run it from the repository root:

```bash
uv run --no-sync python examples/04_custom_backend.py
```

Excerpt from a successful output:

```json
[
  {
    "device_id": "reader-01",
    "status": "succeeded",
    "result": {"values": {"A1": 0.123}, "synthetic": true}
  },
  {
    "device_id": "reader-02",
    "status": "succeeded",
    "result": {"values": {"A1": 0.246}, "synthetic": true}
  }
]
```

The IDs and readings come from the two [instance configurations](../examples/devices), which share one capability definition and backend implementation. This example uses `DemonstrationReaderSDK` to simulate a plate reader SDK and return configured synthetic readings in `mock` mode.

The complete [adapter package](../examples/adapters) has this structure:

```text
examples/adapters/
├── pyproject.toml
└── example_lab/
    ├── __init__.py
    └── plate_reader/
        ├── __init__.py
        ├── models/example_reader.json
        ├── schemas.py
        └── backend.py
```

| File | Purpose |
| --- | --- |
| [models/example_reader.json](../examples/adapters/example_lab/plate_reader/models/example_reader.json) | Define `example_reader.read_absorbance`, accepting a plate ID and wavelength and returning readings by well |
| [schemas.py](../examples/adapters/example_lab/plate_reader/schemas.py) | Load the model definition from the package |
| [backend.py](../examples/adapters/example_lab/plate_reader/backend.py) | Create the SDK client, execute requests, and return results and state |
| [pyproject.toml](../examples/adapters/pyproject.toml) | Declare the package name, dependencies, and Python packages to install |

### 2. Map the capability to SDK calls

This section walks through the template's demonstration calls; the example SDK only returns synthetic readings. The capability's `input_schema` accepts `plate_id` and `wavelength_nm`. The caller submits arguments in this format:

```json
{"plate_id": "plate-001", "wavelength_nm": 600}
```

The backend loads the separately stored model definition and supplies its capabilities to SCP-Lab for capability discovery and request validation:

```python
model = get_model()
self.capabilities = model.capabilities
```

During execution, `request.arguments` is the argument object above. The example uses `execute()` to call the SDK, report progress, and return readings with completion evidence:

```python
async def execute(self, request: ExecutionRequest, context: ExecutionContext) -> BackendResult:
    context.report_progress({"stage": "reading"})
    reading = await self.sdk.read_absorbance(**request.arguments)
    self.observation = StateObservation(
        values={"last_plate_id": request.arguments["plate_id"]},
        observed_at=datetime.now(timezone.utc).isoformat(),
        source="demonstration_reader_sdk",
        kind="simulated",
    )
    return BackendResult(
        result=reading, completion_evidence=CompletionEvidence(kind="mock_trace")
    )
```

The `reading` becomes the execution record's `result`, whose fields must conform to the capability's `result_schema`. The `self.observation` stores the last plate and observation time; `read_state()` supplies it for state queries:

```python
def read_state(self) -> BackendState:
    return BackendState(observation=self.observation)
```

Clients calling `get_device_state` can read the last plate ID from `observation.values.last_plate_id`, alongside the observation time, source, and `simulated` label.

The instance configuration creates a backend through `create_backend(config)`. Here, `synthetic_absorbance` comes from the configuration's `options`:

```python
def create_backend(config: DeviceConfig) -> DeviceBackend:
    Contract.model_validate(config.connection)
    options = ReaderOptions.model_validate(config.options)
    return MyReaderBackend(config, DemonstrationReaderSDK(options.synthetic_absorbance))
```

A hardware integration can validate connection settings such as device addresses and ports here, then create the SDK client. See [backend.py](../examples/adapters/example_lab/plate_reader/backend.py) for the complete class and imports.

### 3. Install and register the adapter

Install the adapter in the Python environment running the SCP-Lab server. The instance configuration's `backend` setting specifies the import path of a Python module and factory function, which the server uses to load the installed adapter.

**Copy the template**

We recommend maintaining the device backend as a separate Python package so it can be updated and released independently of SCP-Lab. This example places the adapter project next to the SCP-Lab repository. You can choose any location, including inside the repository; use the corresponding path in the installation command.

Copy the entire `examples/adapters/` directory next to the SCP-Lab repository and name the copy `my_lab_backend/`. This example uses the following layout:

```text
workspace/
├── scp-lab/                  # SCP-Lab repository
└── my_lab_backend/           # Copied adapter project
    ├── pyproject.toml
    └── example_lab/
```

Keep the internal `example_lab/` directory for this example; the Python import paths below therefore still start with `example_lab`. Make subsequent changes in the copied `my_lab_backend/` project.

**Install in the SCP-Lab environment**

Run from the SCP-Lab repository root. The path `../my_lab_backend` points to the copy made above:

```bash
uv pip install --python .venv/bin/python --no-deps -e ../my_lab_backend
```

On Windows, replace `.venv/bin/python` with `.venv/Scripts/python.exe`. If you keep the adapter project elsewhere, replace `../my_lab_backend` with its actual path.

The `-e` option installs the package for development; restart the server after editing adapter code. The `--no-deps` option skips dependency installation: the base setup already installed SCP-Lab, and the demonstration SDK needs no additional dependencies.

Confirm that the current environment can import the copied package:

```bash
uv run --no-sync python -c "import example_lab; print(example_lab.__file__)"
```

The output path should point to `my_lab_backend/example_lab/__init__.py`.

**Save the device configuration**

Create `lab-devices/` in the SCP-Lab repository root if it does not exist, then save the following as `lab-devices/reader-01.json`. If you saved the earlier offline reader configuration, replace that file's contents to switch `reader-01` to the newly installed backend:

```json
{
  "device_id": "reader-01",
  "backend": "example_lab.plate_reader.backend:create_backend",
  "connection": {},
  "options": {"synthetic_absorbance": 0.123}
}
```

The `backend` setting names the `create_backend` function in the copy's `example_lab/plate_reader/backend.py`. The `options.synthetic_absorbance` value sets the demonstration reading.

**Check and connect**

Still from the SCP-Lab repository root:

```bash
uv run --no-sync scp-lab check --devices-dir ./lab-devices
uv run --no-sync scp-lab mcp-config --devices-dir ./lab-devices --output mcp-config.json
```

The `check` result should have `status="passed"`, confirming that configuration and interface checks passed. Follow the [application guide](clients.md) to merge the generated MCP configuration into your client's configuration and restart the server.

The `describe_device` response includes `example_reader.read_absorbance` and its input fields. Core request submission:

```python
accepted = await call(client, "submit_execution", {
    "request": {
        "device_id": "reader-01",
        "capability_id": "example_reader.read_absorbance",
        "arguments": {"plate_id": "plate-001", "wavelength_nm": 600}
    }
})
```

Continue querying `get_execution` with `accepted["run_id"]`. On success, `result.values.A1` is the configured `0.123`, `result.synthetic` is `true`, and completion evidence is `mock_trace`. Another JSON file with a distinct ID and configuration value registers a second instance, as with `reader-02` in the complete example.

### 4. Connect physical hardware

Physical device integration requires calls through device control software, a vendor SDK, or another control interface. This section uses the `my_lab_backend/` project copied and installed in the previous section: first refine the schemas and parameter validation, then replace the example SDK calls with actual device calls.

The paths and class names below come from the plate reader example; use the corresponding files and backend class for other devices. The `pyproject.toml` and files under `example_lab/` are inside `my_lab_backend/`; device instance configurations stay in the SCP-Lab repository's `lab-devices/` directory.

**First edit the schemas and parameter validation**

| File to edit in this example | Changes |
| --- | --- |
| `example_lab/plate_reader/models/example_reader.json` | Adjust operation names, input fields, units, and parameter ranges for the actual device |
| `example_lab/plate_reader/schemas.py` | If you rename or move the model JSON, update its loading path in `get_model()`; otherwise leave this file as it is |
| `example_lab/plate_reader/backend.py` | For checks beyond the schema, implement `validate(request)` in the backend class and retain the checks from `super().validate(request)`; the backend class in this example is `MyReaderBackend` |

These checks must not start an experiment. Before connecting the actual interface, you can still use `mock` to verify the call flow. Update the demonstration implementation whenever the capability's input or result format changes. In this example, update `DemonstrationReaderSDK` and its calling code in the same `backend.py`.

**Then edit the backend to use the SDK**

Add the SDK dependencies to `my_lab_backend/pyproject.toml`, then run the installation command from the SCP-Lab repository root. Omit `--no-deps` this time so the new dependencies are installed:

```bash
uv pip install --python .venv/bin/python -e ../my_lab_backend
```

Use the same Windows interpreter-path substitution as in the previous section. Then edit `my_lab_backend/example_lab/plate_reader/backend.py`; all of the following changes are in this file:

| Where to edit in this example | Changes |
| --- | --- |
| `create_backend(config)` | Define and validate the required `connection` and `options` settings, then use them to create the real SDK client in place of this example's `DemonstrationReaderSDK` |
| `description` in `MyReaderBackend.__init__()` | Set `execution_mode="hardware"` and `physical_execution=True` |
| `execute(request, context)` | Map request parameters to SDK calls, format the actual results, and return completion evidence based on device feedback |
| `read_state()` and observation updates | Return availability and cached observations, retaining their time, source, and kind |

If the device uses an HTTP service or serial connection, implement those calls in the same file. Place device operations in `execute()`; backend construction, default resolution, validation, and state reads must not start an experiment. Blocking SDK calls can run in a worker thread; send progress back to the event loop before calling `context.report_progress(...)`.

Return `device_released=True` once the device can accept another operation. Return `unknown` if the outcome cannot be confirmed; the device remains in `needs_attention`. A backend supporting cancellation must also confirm that the operation stopped. See [completion evidence](device-access.md#completion-evidence) and the [execution lifecycle](device-access.md#execution-lifecycle-and-occupancy).

**Update result definitions and device configuration**

Update `result_schema` and `completion_criteria` in `my_lab_backend/example_lab/plate_reader/models/example_reader.json` to match the SDK's actual feedback. This example's results require `synthetic=true`; remove or adjust that requirement for hardware so that result formats and completion conditions match the actual feedback.

In the SCP-Lab repository's `lab-devices/reader-01.json`, put device addresses, ports, and other settings in the `connection` fields supported by your backend. Remove the demonstration setting `options.synthetic_absorbance` and supply any options the implementation needs. This example keeps `reader-01`; if the Python module and factory-function path are unchanged, keep the existing `backend` value.

Maintain capability definitions, backend code, and call examples together, updating them when parameters, result fields, or completion conditions change.

**Restart and verify**

The earlier `-e` installation means that restarting the server loads changes to code and model JSON in the same project. Keep the existing MCP configuration if the server startup command and device directory are unchanged. After restarting, run this command from the SCP-Lab repository root:

```bash
uv run --no-sync scp-lab check --devices-dir ./lab-devices
```

The `check` command checks descriptor and state formats. Then follow the previous section's call flow: use `describe_device` to confirm `execution_mode="hardware"`, submit requests using the updated capability definitions, and query the results. Check parameter handling, results, and completion evidence against the definitions, as well as invalid input, failure, and supported cancellation paths.

To add another device using the same capability definitions and backend, add an instance configuration with a different `device_id`; there is no need to copy the project again. For a device requiring different control code, you can add a directory under `my_lab_backend/example_lab/` and point its new instance configuration to the corresponding backend factory.

## Validation and execution stages

The `execution_mode` states how the instance currently handles calls. Devices can support different modes and do not have to progress through them in order.

| Execution mode | What the call does | Typical result | Meaning of success |
| --- | --- | --- | --- |
| `schema_validation` | Check the request against published schemas | Validation report | Request formats and declared constraints passed validation |
| `mock` | Run a demonstration flow | Synthetic readings or demonstration record | The demonstration flow completed |
| `official_simulation` | Call an official simulator | Simulation record | The simulated program completed |
| `hardware` | Operate hardware through the device control interface | Actual readings or device feedback | Actual feedback supports the declared completion conditions |

Input formats, result formats, and completion conditions can differ between execution modes, as described by the selected instance's `input_schema`, `result_schema`, and `completion_criteria`, respectively. The `completion_evidence` records the evidence provided by the call.

On submission, the runtime checks the input schema, [handles defaults according to the declared policy](device-access.md#units-and-defaults), and calls the backend's `validate()`. It calls `execute()` after accepting the request. Successful results are checked against `result_schema` and made available through `get_execution`.

Read the selected instance's descriptor through `describe_device` before calling it. For example, `ot2-validation` and `ot2-sim` have different input schemas, so construct requests using each instance's format.

## Device instance configuration reference

| Field | Meaning |
| --- | --- |
| `schema_version` | Defaults to `scp-lab.device-config.v0.1` |
| `device_id` | Required unique instance ID, stable across restarts |
| `backend` | Required; specify the module and function that creates the backend. See the [format](#how-a-backend-factory-works). The returned backend provides the device `description`, the `capabilities` list, and methods for request validation (`validate()`), execution (`execute()`), and state queries (`read_state()`) |
| `display_name` | Optional label overriding the adapter's default |
| `enabled` | Boolean, defaults to `true`; disabled instances are not constructed |
| `connection` | Adapter-specific connection settings, defaults to `{}` |
| `options` | Adapter-specific configuration, defaults to `{}` |

The [configuration schema](../schemas/device-config.schema.json) defines the instance file's fields. Each adapter validates its own connection settings and options. Keep device addresses and credentials in local configuration or adapter-managed credential sources. File settings use absolute paths unless documented otherwise.

Directory selection is `--devices-dir`, then `SCP_LAB_DEVICES_DIR`, then bundled defaults. Files are read in filename order. Duplicate IDs, including disabled entries, and malformed files are rejected. An empty directory exposes no instances.

| Bundled backend factory | Options | Mode |
| --- | --- | --- |
| `scp_lab.adapters.offline:create_backend` | Use `model_resource` or `model_file` to specify the [capability-definition location](#model-definition-location) | `schema_validation` |
| `scp_lab.adapters.liquid.ot2:create_backend` | Empty; simulator selected by `SCP_LAB_SIM_PYTHON` | `official_simulation` |
| `scp_lab.adapters.heater.backend:create_backend` | Optional `fail` boolean | `mock` |

## Configuration updates and troubleshooting

Model definitions and instance configurations are files; restart the server after modifying them. In this version, common task records exist only in the running server, so the old `run_id` can no longer be queried after a restart. Independently launched servers also do not know whether each other's devices are busy. See the [application guide](clients.md#4-handle-outcomes) for handling these cases. OT-2 simulation records are saved separately as JSON files.

| Symptom | Action |
| --- | --- |
| Adapter cannot be imported | Install it in the interpreter named by the MCP configuration. Regenerate configuration after moving environments. |
| Model cannot be loaded | Check the reported filename, package resource, or absolute local path. Keep model files outside the instance directory. |
| Default examples disappeared | An explicit device directory replaces defaults; copy any desired bundled configurations into it. |
| Duplicate device ID | Use a unique ID in every instance file, including disabled entries. |
| `needs_attention` after a task | Inspect the execution record and actual device state to establish how far the operation progressed. This version has no interface to clear occupancy manually; restarting the server does not prove the device stopped. |
