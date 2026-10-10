# OT-2 simulation: an advanced tutorial

[简体中文](zh-CN/ot2-examples.md) · [Documentation](README.md) · [Home](../README.md) · [First device call](getting-started.md) · [Device integration](backends.md)

This advanced tutorial builds on the request-and-feedback pattern in the [first device call](getting-started.md). You will ask SCP-Lab to transfer 50 µL from well A1 to B1 of a plate. The OT-2 backend generates a Python protocol from the request, runs it in the official Opentrons simulator, and returns execution status and a simulation record through SCP-Lab. The entire example runs on your computer, with no physical robot required.

First complete the [OT-2 environment setup](installation.md#ot-2-simulation).

## Query the input format

Use `describe_device` to obtain the input format for `ot2.liquid_transfer`. The key steps below use the `call()` helper from [device_client.py](../examples/device_client.py), with `client` representing an established MCP session:

```python
# Example helper: call an MCP tool and return the response's data.
from examples.device_client import call

# Query device capabilities and obtain the transfer function's input schema.
descriptor = await call(client, "describe_device", {"device_id": "ot2-sim"})
capability = next(
    item for item in descriptor["capabilities"]
    if item["capability_id"] == "ot2.liquid_transfer"
)
input_schema = capability["input_schema"]

# Inspect the required transfer parameter fields.
print(input_schema["properties"]["parameters"]["required"])
```

The three required fields correspond to the source, destination and transfer volume:

```text
['source', 'destination', 'volume_ul']
```

This example transfers 50 µL from plate well A1 to B1, giving the following `arguments.parameters`:

```json
{
  "source": {"labware": "plate", "well": "A1"},
  "destination": {"labware": "plate", "well": "B1"},
  "volume_ul": 50
}
```

The repository includes a complete [request file](../examples/requests/ot2_execution.json), including `setup` and `liquids`. Their formats are also defined by `input_schema`; the specific pipette, deck layout and initial volumes are predefined for this example.

## Run the simulation example

The [example script](../examples/ot2_simulation.py) reads the supplied request file, submits it and retrieves the result. The script contains the complete invocation code.

From the repository root, select the simulator's Python interpreter and run the example. Set the environment variable again whenever you open a new terminal.

macOS/Linux:

```bash
export SCP_LAB_SIM_PYTHON="$PWD/.venv-sim/bin/python"
uv run --no-sync python examples/ot2_simulation.py
```

Windows PowerShell:

```powershell
$env:SCP_LAB_SIM_PYTHON = "$PWD/.venv-sim/Scripts/python.exe"
uv run --no-sync python examples/ot2_simulation.py
```

## L3 liquid transfer and execution flow

`ot2-sim` uses L3 access to expose `ot2.liquid_transfer` as a parameterized device function. With this access model, the caller specifies the source well, destination well, and volume, while the backend defines the function's internal operation sequence in advance.

After validating the request, the OT-2 backend generates a protocol following this L3 function's predefined sequence: pick up a tip → aspirate → dispense → drop the tip. The generated transfer code is:

```python
pipette.pick_up_tip()
pipette.aspirate(50.0, labware['plate']['A1'])
pipette.dispense(50.0, labware['plate']['B1'])
pipette.drop_tip()
```

The official simulator executes the protocol. Execution status, operation logs, and error information are returned to the caller through SCP-Lab.

## Execution results

The [example script](../examples/ot2_simulation.py) calls `submit_execution` through a local MCP session to start the task, then polls `get_execution` for its status until execution finishes. It prints the execution status and displays the record's `result` as `simulation`.

### Status queries

While the task is running, the execution record in the `data` returned by `get_execution` contains the following status (excerpt):

```json
{
  "status": "running",
  "result": {}
}
```

`running` means the task is still executing, and `result` does not yet contain the final result. After successful completion, the same query returns `status: succeeded` with the simulation record in `result`.

### Example script output

`ot2_simulation.py` prints the final result after execution finishes. The following output indicates successful execution (excerpt):

```json
{
  "status": "succeeded",
  "execution_mode": "official_simulation",
  "physical_execution": false,
  "completion_evidence": {
    "kind": "official_simulator_runlog"
  },
  "simulation": {
    "run_id": "ff1f6fe6-c947-4fd7-8d3e-9287eabb1eb6",
    "sdk_version": "8.8.2"
  }
}
```

`status: succeeded` indicates that the generated protocol completed successfully in the official simulator, with the simulator run log as completion evidence. `physical_execution: false` means no physical device was operated.

### Save and read simulation records

After simulation finishes, the output's `simulation` object is saved as `.scp-lab/runs/<simulation-record-id>.json`. It contains the generated protocol, operation log and preflight results. Its ID is `simulation.run_id`, with a new value generated for each run.

From the repository root, run the following command, replacing `SIMULATION_RUN_ID` with the `simulation.run_id` from your output:

```bash
uv run --no-sync scp-lab run SIMULATION_RUN_ID
```

This command reads the saved record. The outer `run_id` is used for `get_execution` queries in the current MCP session. If `SCP_LAB_RUN_DIR` is set, records are saved in that directory; use the same setting when reading them.

### Operation log

`simulation.commands` contains the simulator's operation log. The `text` values of these four records correspond to the four operations in the transfer code (excerpt):

```text
Picking up tip from A1 of Opentrons OT-2 96 Tip Rack 300 µL on slot 1
Aspirating 50.0 uL from A1 of NEST 96 Well Plate 200 µL Flat on slot 3 at 92.86 uL/sec
Dispensing 50.0 uL into B1 of NEST 96 Well Plate 200 µL Flat on slot 3 at 92.86 uL/sec
Dropping tip into Trash Bin on slot 12
```

The log shows the simulator picking up a tip, aspirating 50 µL from A1, dispensing 50 µL into B1, and dropping the tip, in that order. The full generated protocol is in `simulation.generated_code`; `simulation.sdk_version` records the SDK version used, `8.8.2` in this run.

### Preflight checks

`simulation.validation` contains SCP-Lab's preflight results. Tip count and predicted well volumes for this example (excerpt):

```json
{
  "required_tips": 1,
  "predicted_wells": [
    {"location": "plate/A1", "volume_ul": 150.0},
    {"location": "plate/B1", "volume_ul": 50.0}
  ]
}
```

The operation requires one tip. A1 is predicted to decrease from its declared 200 µL to 150 µL, while the initially empty B1 increases to 50 µL. These are preflight predictions calculated from the declared initial volumes and transfer parameters. The simulator log confirms that the protocol can execute in the simulated environment; actual transferred volumes and liquid behavior still require physical experiments to verify.

Try changing `arguments.parameters.volume_ul` in the request file and running the example again. Compare the generated protocol, operation log, and predicted volumes. When changing the source well, also declare its initial volume in `arguments.liquids`.

This tutorial displays feedback in the terminal and JSON output. For graphical previews, see the official [OT-2 App visualization guide](https://docs.opentrons.com/ot-2/opentrons-app/protocol-viz/).

To make this backend available to another MCP client, regenerate its [local configuration](clients.md):

```bash
uv run --no-sync scp-lab mcp-config --output mcp-config.json
```

## Capabilities and setup

Inspect the full device descriptor, including each capability's input and result schemas:

```bash
uv run --no-sync scp-lab device ot2-sim
```

The output's `capabilities` array contains the capability list. Each entry identifies its name and access level with `capability_id` and `access_level`. Extract just these fields from the `descriptor` returned by the earlier `describe_device` call:

```python
for capability in descriptor["capabilities"]:
    print(capability["capability_id"], capability["access_level"] or "-")
```

```text
ot2.liquid_transfer L3
ot2.liquid_distribution L3
ot2.liquid_consolidation L3
ot2.pipette_mixing L3
ot2.incubation L3
ot2.orbital_shaking L3
ot2.thermal_cycling L3
ot2.magnetic_separation L3
ot2.delay -
```

The eight entries marked `L3` are device functions. `ot2.delay` is a helper wait step with `access_level: null`, displayed here as `-`.

This simulation backend supports single-channel pipettes. Each transfer from one well to another, or each mixing function call, uses a fresh tip. Distribution and consolidation execute as follows:

| Function | Example request | Execution order |
| --- | --- | --- |
| Distribution | Transfer 50 µL each from A1 to B1 and B2 | Transfer 50 µL from A1 to B1, then 50 µL from A1 to B2 |
| Consolidation | Collect 50 µL each from A1 and A2 into B1 | Transfer 50 µL from A1 to B1, then 50 µL from A2 to B1 |

For operations on a Temperature Module, Heater-Shaker or other module, set the plate's location to that module in `setup`. For example, the [temperature-hold example](../examples/protocols/temperature_hold.json) sets the plate's `location` to the Temperature Module's ID, `module`. Simulation starts with the plate already on that module; the protocol contains no operation to move the plate there from another location.

Preflight checks verify that the labware is supported and that the transfer volume is within the selected pipette's range.

The separate `ot2-validation` instance has ten schema-validation actions. Its arguments and execution mode differ from those of `ot2-sim`.

## More experiment examples

Beyond a single liquid transfer, the repository includes simulation examples for serial dilution, sample pooling, temperature control, shaking, thermal cycling and magnetic operations. Each file includes the required setup and initial volumes, with one or more operations listed in `steps`.

| Input | Example |
| --- | --- |
| [serial_dilution.json](../examples/protocols/serial_dilution.json) | Distribute diluent, transfer serially, and mix |
| [pooling.json](../examples/protocols/pooling.json) | Consolidate two sources, mix, and wait |
| [temperature_hold.json](../examples/protocols/temperature_hold.json) | Hold a Temperature Module at a specified temperature for a set duration |
| [heater_shaker.json](../examples/protocols/heater_shaker.json) | Run a Heater-Shaker at a specified speed for a set duration |
| [thermal_profile.json](../examples/protocols/thermal_profile.json) | Run a Thermocycler with specified temperatures, hold times and cycle count |
| [magnetic_hold.json](../examples/protocols/magnetic_hold.json) | Engage a Magnetic Module, hold for a set duration, then disengage |

For the serial-dilution example:

```bash
# Check that the inputs and setup meet execution requirements.
uv run --no-sync scp-lab validate examples/protocols/serial_dilution.json
# Generate a Python protocol for inspection.
uv run --no-sync scp-lab compile examples/protocols/serial_dilution.json -o build/serial_dilution.py
# Execute in the official simulator.
uv run --no-sync scp-lab simulate examples/protocols/serial_dilution.json
```

`validate` checks that wells are valid, labware items do not occupy the same slot, required modules and enough tips are configured, and source wells contain enough declared liquid for the transfers. It also checks that parameters such as volume and temperature are within allowed ranges.

Use the `run_id` returned by `simulate` to [read the saved simulation record](#save-and-read-simulation-records).

Inspect the included [generated code](../examples/results/serial_dilution.py) and [official simulation record](../examples/results/serial_dilution.simulation.json) for a worked example.

## OT-2-specific tools

The reference server provides these OT-2-specific MCP tools to check the experimental protocols above, generate code and run simulations:

| Tool | Purpose |
| --- | --- |
| `capabilities` | Query operations, parameter formats and labware supported by the OT-2 backend |
| `validate_protocol` | Check an OT-2 protocol's parameters, setup and liquid volumes |
| `compile_protocol` | Convert an OT-2 experimental protocol into Python code |
| `simulate_protocol` | Run official simulation and return its record when complete |
| `invoke_capability` | Generate code for one OT-2 operation by default; use `mode="simulate"` to run simulation |
| `read_simulation_run` | Read a saved result by its simulation record ID |

For example, validate, compile and simulate the serial-dilution protocol through MCP:

```bash
# Validate the input and generate code.
uv run --no-sync python examples/mcp_client.py examples/protocols/serial_dilution.json
# Also run official simulation after validation and code generation.
uv run --no-sync python examples/mcp_client.py examples/protocols/serial_dilution.json --simulate
```

The earlier [device-call example](../examples/ot2_simulation.py) uses `describe_device`, `submit_execution` and `get_execution` for capability discovery, task submission and status queries. The tools in this section process OT-2 experimental protocols directly; see the [interface reference](device-access.md#errors-and-schemas) for their response formats and task-management behavior.

SDK reference: [Opentrons execution and simulation documentation](https://docs.opentrons.com/python-api/reference/execute-simulate/).
