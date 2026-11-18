# Connect laboratory instruments through SCP-Lab

[简体中文](zh-CN/http-instruments.md) · [Backend guide](backends.md)

Use SCP-Lab to acquire images and measurements, identify an Opentrons robot at the bench, or read the Bioyond scheduler state. Each configured instance exposes its supported operations through the same SCP-Lab MCP interface. Software tests use local instrument protocol fixtures. Physical commissioning is pending.

| Service | SCP-Lab capability | What a successful call establishes |
| --- | --- | --- |
| Opentrons OT-2 / Flex | `opentrons.get_rail_lights` | The robot server reports the rail lights on or off. |
| Opentrons OT-2 / Flex | `opentrons.set_rail_lights` | A separate read after the write matches the requested boolean. An operator can confirm the light at the bench. |
| Bioyond Studio LIMS | `bioyond.get_scheduler_status` | The service reports success and returns its scheduler state, for example `Stop`. Individual instruments have their own states. |

The SCP-Lab adapters use the [Opentrons HTTP API](https://docs.opentrons.com/http/api_reference.html) v2 light operations and the Bioyond Studio LIMS status service. Confirm the Bioyond LIMS endpoint and credentials with the site operator.

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

## Measurement and imaging hardware

Each row has a separate SCP-Lab instance file and an acquisition you can submit. Copy the file for the hardware at your site into `lab-devices/` and replace the example connection settings. The model links are the project or manufacturer's interface definitions.

| Model and API | Instance file | SCP-Lab capability | Result |
| --- | --- | --- | --- |
| [OpenFlexure Microscope](https://openflexure.gitlab.io/openflexure-microscope-server/http/openapi.json) | [openflexure_microscope.json](../examples/measurement-devices/openflexure_microscope.json) | `openflexure_microscope.snapshot` | JPEG preview, byte count, SHA-256 and server-local file URI |
| [EEZ Bench Box 3 (BB3)](https://www.envox.eu/eez-bench-box-3/bb3-scpi-reference-manual/5-subsystem-command-reference/) | [eez_bb3.json](../examples/measurement-devices/eez_bb3.json) | `eez_bb3.read_voltage` | Measured sense-terminal voltage (V) on the configured channel |
| [Red Pitaya STEMlab 125-14](https://redpitaya.readthedocs.io/en/latest/appsFeatures/examples/analog/ana-1-read_analog_inputs.html) | [stemlab_125_14.json](../examples/measurement-devices/stemlab_125_14.json) | `stemlab_125_14.read_voltage` | Slow analog input voltage (V) on AIN0–AIN3 |
| [Tinkerforge Load Cell Bricklet 2.0](https://github.com/Tinkerforge/generators/blob/master/configs/bricklet_load_cell_v2_config.py) | [load_cell_v2.json](../examples/measurement-devices/load_cell_v2.json) | `load_cell_v2.read_weight` | Weight from the attached calibrated load cell (g) |
| [Tinkerforge CO2 Bricklet 2.0](https://github.com/Tinkerforge/generators/blob/master/configs/bricklet_co2_v2_config.py) | [co2_v2.json](../examples/measurement-devices/co2_v2.json) | `co2_v2.read_co2` | Ambient CO₂ concentration (ppm) |
| [Tinkerforge Color Bricklet 2.0](https://github.com/Tinkerforge/generators/blob/master/configs/bricklet_color_v2_config.py) | [color_v2.json](../examples/measurement-devices/color_v2.json) | `color_v2.read_color` | Four raw photodiode counts (red, green, blue and clear) |
| [Tinkerforge Humidity Bricklet 2.0](https://github.com/Tinkerforge/generators/blob/master/configs/bricklet_humidity_v2_config.py) | [humidity_v2.json](../examples/measurement-devices/humidity_v2.json) | `humidity_v2.read_humidity` | Relative humidity (%RH) |

- **Microscope.** Use an OpenFlexure server exposing `GET /camera/snapshot` (v3 API). Configure an existing writable absolute `output_dir` on the SCP-Lab host. Open the returned file there and compare it with the live view. Each call creates a new image.
- **Electrical measurements.** Enable the instrument's Ethernet SCPI server. On the BB3 select an installed voltage-measuring channel; on the STEMlab select a slow analog input on the extension connector. Compare the voltage with the instrument display or a reference meter.
- **Bricklet measurements.** These four open-hardware modules connect through a Brick and a Brick Daemon or compatible gateway. Install the optional Python bindings in the SCP-Lab environment with `uv pip install --python .venv/bin/python -e './examples/adapters[bricklets]'`. Enter the host, port and each module's own UID from Brick Viewer. These examples use a gateway with unauthenticated bindings enabled. Compare readings with Brick Viewer; for weighing, verify the attached load cell with a known mass.

For example, submit this argument object through SCP-Lab for the configured scale, then poll its run. All seven acquisitions accept an empty arguments object.

```json
{"request":{"device_id":"load_cell_v2","capability_id":"load_cell_v2.read_weight","arguments":{}}}
```

## Verify the connection

Check registration and generate the configuration for your MCP client.

```bash
uv run --no-sync scp-lab check --devices-dir lab-devices
uv run --no-sync scp-lab mcp-config --devices-dir lab-devices -o mcp-config.json
```

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
