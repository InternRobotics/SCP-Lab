# Connect an Opentrons robot or a Bioyond Studio scheduler

[简体中文](zh-CN/http-instruments.md) · [Backend guide](backends.md)

Use these optional adapters to identify an OT-2 or Flex at the bench, or to see the state reported by a Bioyond Studio scheduler. Each adapter calls a configured HTTP service. The tests exercise the request and response contracts against a local HTTP fixture. Physical commissioning is pending.

| Service | SCP-Lab capability | What a successful call establishes |
| --- | --- | --- |
| Opentrons OT-2 / Flex | `opentrons.get_rail_lights` | The robot server reports the rail lights on or off. |
| Opentrons OT-2 / Flex | `opentrons.set_rail_lights` | A separate read after the write matches the requested boolean. An operator can confirm the light at the bench. |
| Bioyond Studio LIMS | `bioyond.get_scheduler_status` | The service reports success and returns its scheduler state, for example `Stop`. Individual instruments have their own states. |

The light operations use version 2 of the [Opentrons HTTP API](https://docs.opentrons.com/http/api_reference.html). The Bioyond contract follows the public [Uni-Lab-OS scheduler client](https://github.com/deepmodeling/Uni-Lab-OS/blob/43923ec9473e2f6d33d3ca1ebca4bf4d507e06b2/unilabos/devices/workstation/bioyond_studio/bioyond_rpc.py#L1008-L1023) and its [JSON transport](https://github.com/deepmodeling/Uni-Lab-OS/blob/43923ec9473e2f6d33d3ca1ebca4bf4d507e06b2/unilabos/device_comms/rpc.py). Confirm the LIMS interface with the site's Bioyond Studio operator.

## Register a local instance

After the [base installation](installation.md), run these commands in the SCP-Lab repository.

```bash
uv pip install --python .venv/bin/python --no-deps -e examples/adapters
mkdir -p lab-devices
```

Save one JSON file per service you have. Replace the example addresses with site values. For an OT-2 or Flex, save `lab-devices/robot-01.json` with the robot server's address (normally port 31950).

```json
{
  "device_id": "robot-01",
  "backend": "example_lab.opentrons.backend:create_backend",
  "connection": {"base_url": "http://robot-01.example.invalid:31950"}
}
```

For Bioyond Studio, save `lab-devices/studio-01.json`. Set the service origin and the absolute path to a local text file containing the API key. The SCP-Lab server process reads the file when the capability is called.

```json
{
  "device_id": "studio-01",
  "backend": "example_lab.bioyond.backend:create_backend",
  "connection": {
    "base_url": "https://studio.example.invalid",
    "api_key_file": "/absolute/path/to/bioyond-key"
  }
}
```

Check registration and generate the configuration for your MCP client.

```bash
uv run --no-sync scp-lab check --devices-dir lab-devices
uv run --no-sync scp-lab mcp-config --devices-dir lab-devices -o mcp-config.json
```

## Verify the connection

Connect your client using the generated config. Call `describe_device` with the configured device ID. Registration only loads the local descriptor. To contact a service, call `submit_execution` with one of these complete argument objects, then poll `get_execution` with the returned `run_id` in the same MCP session.

```json
{"request":{"device_id":"robot-01","capability_id":"opentrons.get_rail_lights","arguments":{}}}
```

```json
{"request":{"device_id":"studio-01","capability_id":"bioyond.get_scheduler_status","arguments":{}}}
```

For a light check, record the initial `result.on`, set the opposite value, observe the physical light, then restore the original value. This example requests **on**.

```json
{"request":{"device_id":"robot-01","capability_id":"opentrons.set_rail_lights","arguments":{"on":true}}}
```

A successful record has `completion_evidence.kind = "device_reported"`. For Bioyond, compare `result.schedulerStatus` with the Studio display. For an uncertain light write, inspect the robot before retrying. A lost acknowledgement or unreadable readback produces `unknown`; a valid readback that disagrees with the request produces `failed` and includes the observed value.

## What to collect from the facility

For the next instrument, record its model and installed software version, whether the facility scheduler or the instrument owns its control interface, and which operation the site wants to expose first. Obtain a versioned API or SDK, its authentication method, one successful and one failed response, and the operator's criterion for completion. Use these to build the capability definition, implement the backend, and commission a named instance. Keep actual addresses and credentials in local configuration.
