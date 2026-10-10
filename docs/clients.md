# Connect your application or agent to SCP-Lab

[简体中文](zh-CN/clients.md) · [Documentation](README.md) · [Home](../README.md) · [First device call](getting-started.md) · [Connect your devices](backends.md)

Use this guide when you want your own software to **call** laboratory capabilities. SCP-Lab exposes a local MCP server; you choose the application, agent framework, and experiment logic. To **expose** an instrument or SDK instead, use the [device integration guide](backends.md).

The project includes interface definitions for 45 models, each with an offline validation instance, providing 89 capabilities. Use them to [test agent discovery, request construction, and multi-step calls](#bundled-device-interface-environment) without connecting hardware.

## 1. Connect an MCP-compatible application

Complete the [installation](installation.md), then run from the repository root:

```bash
uv run --no-sync scp-lab mcp-config --output mcp-config.json
```

The generated file contains an `mcpServers.scp-lab` entry with:

| Field | Meaning |
| --- | --- |
| `command` | Absolute path to the Python interpreter with SCP-Lab installed |
| `args` | `-m scp_lab.server` |
| `env` | Local backend and simulator settings, when configured |

If your client accepts an `mcpServers` configuration file, merge the `scp-lab` entry into its existing configuration. If it has separate UI fields, copy the entry's command, arguments, and environment values into its local stdio server settings. Preserve any other MCP servers already configured.

The client launches SCP-Lab as a child process. This implementation uses local **stdio**, so it does not require a remote server URL or SCP platform account. Generate the file on the computer running your client, and regenerate it after moving the repository or changing backend environments. The command writes a file; it does not modify application settings.

To use your own instances, follow [device configuration](backends.md#configure-devices-with-an-existing-backend) and generate the client entry with `--devices-dir`. For the optional OT-2 backend, complete the [simulator setup](installation.md#ot-2-simulation) before regenerating the configuration.

## 2. Discover and call a capability

### Discover available tools

After connecting to SCP-Lab, query the available tools through MCP tool discovery:

```python
tools = await client.list_tools()
for tool in tools.tools:
    print(tool.name, tool.description)
```

Each tool provides a name, a description, and an `inputSchema`. An agent uses this information to learn which interfaces are available and what arguments they accept. The common device tools include:

| Tool | Use it to |
| --- | --- |
| `list_devices` | Discover configured instances, their execution modes, and current state |
| `describe_device` | Read an instance's capabilities, parameter schemas, result schemas, and descriptor revision |
| `submit_execution` | Submit one explicit capability request and obtain a run ID |
| `get_execution` | Poll the run's status, progress, result, errors, and completion evidence |
| `get_device_state` | Read availability, occupancy, and any reported device observations |
| `cancel_execution` | Request cancellation when the descriptor advertises support |

### Discover registered devices

Call `list_devices` with empty arguments to retrieve all registered devices. If you specify `device_class`, only devices of that class are returned.

```python
from examples.device_client import call

devices = await call(client, "list_devices", {})
for device in devices:
    print(device["device_id"], device["display_name"],
          device["execution_mode"], sep=" | ")
```

Excerpt from the default configuration, showing device ID, display name, and execution mode:

```text
agilent_biotek_synergy_h1-validation | Agilent BioTek Synergy H1 (schema validation) | schema_validation
cytomat_6002-validation | Cytomat 6002 (schema validation) | schema_validation
demo-heater | Mock heater | mock
hamilton_star-validation | Hamilton STAR (schema validation) | schema_validation
ot2-sim | OT-2 official simulator | official_simulation
```

The default server registers 48 instances: 45 `schema_validation` interface instances, two `mock` heaters, and one `official_simulation` OT-2 instance. Without the optional simulator environment, OT-2 remains discoverable but reports an unavailable state.

An agent selects candidate devices using the experiment requirements, device names and execution modes, then queries their capabilities. This example selects `demo-heater` from the returned list to demonstrate a mock call.

### Query capabilities and input fields

Pass the returned device ID to `describe_device` to read its capabilities and their descriptions:

```python
device = next(item for item in devices if item["device_id"] == "demo-heater")
descriptor = await call(client, "describe_device", {"device_id": device["device_id"]})
for item in descriptor["capabilities"]:
    print(item["capability_id"], item["description"], sep=" | ")
```

This device returns:

```text
demo_heater.hold | Timed runtime demonstration, no physical heating.
```

Select the returned `demo_heater.hold` capability and read its input fields from `input_schema`:

```python
capability = next(
    item for item in descriptor["capabilities"]
    if item["capability_id"] == "demo_heater.hold"
)
input_schema = capability["input_schema"]
print(list(input_schema["properties"]))
```

The field names are:

```text
['target_celsius', 'duration_s']
```

This example requests a target of 37 °C and a mock duration of 1 second, so the arguments are `target_celsius=37` and `duration_s=1`. The `input_schema` defines parameter types, bounds, units, and defaults; see the [protocol reference](device-access.md#units-and-defaults).

### Submit the request

Put the device ID, capability ID, and those arguments in `request`, then call `submit_execution`:

```python
accepted = await call(client, "submit_execution", {
    "request": {
        "device_id": device["device_id"],
        "capability_id": capability["capability_id"],
        "arguments": {"target_celsius": 37, "duration_s": 1},
        "idempotency_key": "my-heater-call-001",
        "expected_descriptor_revision": descriptor["descriptor_revision"],
    }
})
run_id = accepted["run_id"]
print(accepted["status"], run_id)
```

The returned `status` is `accepted`, and `run_id` identifies this task. The optional `expected_descriptor_revision` checks that the capability description still matches the version you queried. Use `idempotency_key` when retrying the same request; use a new key for a new operation.

### Query status and results

After acceptance, use the task ID to call `get_execution` in the same session:

```python
record = await call(client, "get_execution", {"run_id": run_id})
print(record["status"])
print(record["result"])
```

Each query returns the execution record at that time. While the task is `accepted` or `running`, wait briefly and query again. Read `result` when execution completes.

Excerpt from this example's successful execution record:

```json
{
  "status": "succeeded",
  "execution_mode": "mock",
  "result": {
    "requested_target_celsius": 37,
    "elapsed_demo_seconds": 1,
    "measured_temperature": null
  }
}
```

The `demo-heater` runs a mock timer. Its `measured_temperature` is `null` because no temperature is measured.

## 3. Complete example

| Example | Contents |
| --- | --- |
| [quickstart.py](../examples/quickstart.py) | Discover the demonstration heater, query its capability, submit a request, and read the result |
| [01_device_call.py](../examples/01_device_call.py) | Discover default instances and validate representative requests for selected device models |
| [02_multi_device.py](../examples/02_multi_device.py) | Validate liquid-transfer, incubation, and plate-reading requests in a caller-defined sequence |

Helpers for session setup, tool calls, and polling are in [examples/device_client.py](../examples/device_client.py). These scripts are ordinary MCP clients. When integrating an agent, let it select capabilities and construct requests from device descriptions.

<a id="bundled-device-interface-environment"></a>
### Test an agent with bundled interfaces

The bundled interfaces provide a basic offline environment for agent calls. Use the `list_devices` → `describe_device` → `submit_execution` → `get_execution` flow above to check whether an agent can find suitable devices, select operations, supply arguments according to schemas, and correct rejected requests using error feedback.

Select offline validation instances from the device list:

```python
devices = await call(client, "list_devices", {})
interfaces = [
    device for device in devices
    if device["execution_mode"] == "schema_validation"
]
print({
    "devices": len(interfaces),
    "capabilities": sum(device["capability_count"] for device in interfaces),
})
```

The default configuration returns:

```text
{'devices': 45, 'capabilities': 89}
```

For example, give an agent this task so that it chooses interfaces starting with discovery:

```text
Discover available offline validation devices and design a sequence of liquid
transfer, incubation, and plate reading for sample-plate.
Read candidate capability descriptions, then construct and submit each request
according to its input_schema. If rejected, correct it using the error feedback.
Report the validation outcome of each step.
```

The returned `result.validated_command` is the request that passed schema checks, and `completion_evidence.kind` is `schema_validation`. Use these responses to inspect an agent's interface choices and call sequence, and to check each request's format. Sample existence, actual plate movement, scientific effects, and measured readings require feedback from an execution backend.

Existing examples show the complete call flow:

```bash
# Discover devices and validate representative device requests.
uv run --no-sync python examples/01_device_call.py
# Validate liquid-transfer, incubation, and plate-reading requests in sequence.
uv run --no-sync python examples/02_multi_device.py
```

Requests are in [device_classes.json](../examples/requests/device_classes.json). The multi-device example associates requests using the same `sample-plate` identifier, with the order specified by the script. Individual checks do not simulate changes in liquid volume, sample location, or experimental outcomes. See the [device catalog](devices.md#interface-catalog) for the full model list.

### If bundled interfaces are missing

First call `list_devices` with empty arguments so that a `device_class` filter does not hide other classes. MCP `list_tools` returns generic tools; query devices and their operations through `list_devices` and `describe_device`, respectively.

Check that the `command` in your client's SCP-Lab server configuration points to the current installation, and that its device-directory setting is correct. With `SCP_LAB_DEVICES_DIR` or `--devices-dir`, the server loads only that directory, replacing the default selection. To explicitly load the repository's bundled instances, generate a configuration from the repository root:

```bash
uv run --no-sync scp-lab mcp-config --devices-dir ./src/scp_lab/data/devices --output mcp-config.json
```

Update the client's `scp-lab` entry with the generated settings, restart that server, and call `list_devices` again. To use your own devices alongside selected bundled interfaces, copy the required bundled instance configurations into your device directory; see [device configuration](backends.md#configure-devices-with-an-existing-backend).

## 4. Handle outcomes

### Check the task status

After calling `get_execution`, use the record's `status` to decide what to do next:

| `status` | Meaning | Caller action |
| --- | --- | --- |
| `accepted`, `running` | The request was accepted or is executing | Wait and query again; read `progress` for updates |
| `cancel_requested` | Cancellation was requested; the backend has not confirmed the outcome | Continue querying until a final status is available |
| `succeeded` | Execution succeeded | Read `result` and interpret it with the execution mode and completion evidence |
| `failed` | Execution failed | Read `error.code`, `error.message`, and `error.details` to investigate |
| `cancelled` | The backend confirmed that the operation stopped | Use the cancellation outcome to determine subsequent experiment steps |
| `unknown` | The backend cannot confirm the outcome | Check the device and experiment state before deciding what to do next |

Check tool-query success separately from task-execution success. For example, this response shows a successful lookup of a failed task (excerpt):

```json
{
  "ok": true,
  "data": {
    "status": "failed",
    "error": {
      "code": "demo_heater_fault",
      "message": "Injected mock failure",
      "details": {}
    }
  }
}
```

If the tool call itself fails, for example because the task ID does not exist, the MCP response sets `isError: true`. The `call()` helper used above raises an exception in that case. On success, it returns `data`, so read the task status through `record["status"]`. See the [protocol reference](device-access.md#mcp-tools-and-messages) for the full response format.

### Read results and completion evidence

After successful execution, the capability's `result_schema` defines the fields in `result`. Also read `execution_mode` and `completion_evidence` to understand what the execution checked or performed:

```python
print(record["execution_mode"])
print(record["completion_evidence"]["kind"])
```

The heater example above returns:

```text
mock
mock_trace
```

This means the mock timer completed. OT-2 official simulation returns `official_simulation` and `official_simulator_runlog`, indicating that the program completed software simulation. For hardware execution, the integration backend declares the completion conditions and feedback. See [completion evidence](device-access.md#completion-evidence) for each mode's meaning.

### Cancel, retry, and handle timeouts

- When the device descriptor declares `cancellation_supported=true`, you can call `cancel_execution`. Continue querying after `cancel_requested`; the final status may be `cancelled` or `succeeded` if the operation has already completed.
- If you receive no response after submitting a request, retry with the original request and `idempotency_key` to avoid creating a duplicate task. Use a new key for a new operation; changed arguments with the old key are rejected.
- A timeout means the result has not arrived yet; the device may still be executing. Keep the current connection open and continue querying with the original `run_id`. If the status is `unknown`, inspect device logs or the actual device state to establish how far the operation progressed before deciding whether to resubmit.

In the current version, task records exist only in the running SCP-Lab server. After that server closes or restarts, the original `run_id` can no longer be queried, and the old `idempotency_key` can no longer prevent duplicate submissions. Independently launched servers each track whether a device is busy, so one server should manage a given physical device. See [duplicate submissions and server scope](device-access.md#idempotency-and-session-scope).

This handling applies to the common device tools. The [protocol reference](device-access.md#errors-and-schemas) describes the response formats and simulation records of the [OT-2-specific tools](ot2-examples.md#ot-2-specific-tools).
