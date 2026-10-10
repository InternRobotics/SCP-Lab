# Your first device call

[简体中文](zh-CN/getting-started.md) · [Documentation](README.md) · [Home](../README.md) · [Installation](installation.md) · [Connect your application or agent](clients.md) · [Connect your devices](backends.md)

This optional tutorial walks through a complete device call using a software demonstration device. First complete the [installation](installation.md), then run the commands below from the repository root. No device SDK or laboratory equipment is needed.

## 1. Make your first call

```bash
uv run --no-sync python examples/quickstart.py
```

The script starts an MCP server automatically and keeps one connection open until the request completes. You do not need a second terminal, a hosted account, or a model API key.

It performs this sequence:

1. `list_devices` finds the demonstration heater.
2. `describe_device` retrieves its `demo_heater.hold` capability and input schema.
3. `submit_execution` accepts a request and returns an execution record with a `run_id`.
4. `get_execution` returns the current execution record on each poll. The example queries it every 0.2 seconds and prints status changes until execution finishes.
5. `get_device_state` shows that the device is idle again.

The request in [quickstart.py](../examples/quickstart.py) includes:

```json
{
  "device_id": "demo-heater",
  "capability_id": "demo_heater.hold",
  "arguments": {"target_celsius": 37, "duration_s": 1}
}
```

The script also includes the descriptor revision it just discovered. This lets the server reject a request if the published interface has changed.

## 2. Read the result

The terminal shows each step and the observed status changes. A typical run starts like this (`<run_id>` stands for the actual task ID):

```text
list_devices -> demo-heater (mock)
describe_device -> demo_heater.hold
submit_execution -> accepted (run_id=<run_id>)
Polling get_execution every 0.2 s; showing status changes.
get_execution -> running
get_execution -> succeeded
Result:
```

Polling reads the same task; it does not submit the experiment again. Each response includes the current status and reported progress. The example prints a status only when it changes, then prints the final result:

```json
{
  "status": "succeeded",
  "execution_mode": "mock",
  "physical_execution": false,
  "evidence": "mock_trace",
  "result": {
    "requested_target_celsius": 37,
    "elapsed_demo_seconds": 1,
    "measured_temperature": null
  }
}
```

`evidence` in this example's display is shorthand for `completion_evidence.kind` in the full execution record. The demonstration uses a timer: success means the software task completed, and `measured_temperature` remains `null`. It does not simulate heat transfer or report a physical measurement. The last line is `get_device_state -> idle`.

## 3. Change a parameter

Open [quickstart.py](../examples/quickstart.py) and edit `request.arguments`. Try a different target temperature or a duration of two seconds, then run the same command again.

To inspect the published schema:

```bash
uv run --no-sync scp-lab device demo-heater
```

This device accepts a target from 4 to 95 degrees Celsius and a duration greater than 0 and at most 10 seconds. The schema declares units through `x-scp-unit`. Omitting `duration_s` uses the declared one-second default; `target_celsius` is required. The full execution record preserves both the submitted and effective arguments.

## Choose your next step

| Goal | Guide |
| --- | --- |
| Continue with code generation and official simulation | [Advanced tutorial: OT-2 simulation](ot2-examples.md) |
| Call devices from your own program or agent | [Connect your application or agent](clients.md) |
| Expose your own instrument SDK or lab service | [Connect your devices](backends.md) |
| Explore device interfaces, execution modes, and examples | [Device catalog](devices.md) and [examples](../examples/README.md) |
| Inspect message fields and lifecycle rules | [Protocol reference](device-access.md) |

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| A server launched manually shows no output | A stdio MCP server waits for a client. Run `quickstart.py`, which starts and connects to it. |
| A previously returned run ID cannot be found | Use the same server session for submission and polling. Records are scoped to that process. |
| `ot2-sim` is unavailable | Install the optional simulator environment using the [OT-2 installation steps](installation.md#ot-2-simulation). The quickstart does not need it. |
| A request is rejected | Inspect the device's `input_schema` for required fields, units, types, and ranges. |
