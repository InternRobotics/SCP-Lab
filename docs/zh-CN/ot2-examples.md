# OT-2 仿真：进阶教程

[English](../ot2-examples.md) · [文档目录](README.md) · [首页](../../README.zh-CN.md) · [入门教程](getting-started.md) · [设备接入](backends.md)

本进阶教程沿用[第一次设备调用](getting-started.md)中的请求与反馈流程。你将通过 SCP-Lab 请求从孔板的 A1 孔向 B1 孔转移 50 µL 液体。OT-2 后端根据请求生成 Python 程序，交给官方 Opentrons 仿真器运行，再通过 SCP-Lab 返回执行状态和仿真记录。整个示例在电脑上运行，无需实体机器人。

先完成 [OT-2 仿真环境安装](installation.md#ot-2-simulation)。

## 查询输入格式

通过 `describe_device` 查询 `ot2.liquid_transfer` 的输入格式。关键步骤如下，`call()` 为 [device_client.py](../../examples/device_client.py) 中的调用辅助函数，`client` 为已建立的 MCP 会话：

```python
# 示例辅助函数：调用 MCP 工具并返回响应中的 data。
from examples.device_client import call

# 查询设备能力，获取移液功能的输入 schema。
descriptor = await call(client, "describe_device", {"device_id": "ot2-sim"})
capability = next(
    item for item in descriptor["capabilities"]
    if item["capability_id"] == "ot2.liquid_transfer"
)
input_schema = capability["input_schema"]

# 查看移液参数中的必填字段。
print(input_schema["properties"]["parameters"]["required"])
```

输出的三个必填字段分别对应来源、目标和转移体积：

```text
['source', 'destination', 'volume_ul']
```

本例从孔板 A1 向 B1 转移 50 µL，`arguments.parameters` 填写为：

```json
{
  "source": {"labware": "plate", "well": "A1"},
  "destination": {"labware": "plate", "well": "B1"},
  "volume_ul": 50
}
```

仓库已提供完整的[示例请求文件](../../examples/requests/ot2_execution.json)，其中还包含 `setup` 和 `liquids`。这些字段的格式也由 `input_schema` 定义；具体的移液器、台面布局和初始液量由本例预先指定。

## 运行仿真示例

[示例脚本](../../examples/ot2_simulation.py)直接读取上述请求文件并完成提交和结果查询；完整调用代码可查看该脚本。

在仓库根目录指定仿真环境的 Python 解释器，再运行示例。每次打开新终端时，需要重新设置该环境变量。

macOS/Linux：

```bash
export SCP_LAB_SIM_PYTHON="$PWD/.venv-sim/bin/python"
uv run --no-sync python examples/ot2_simulation.py
```

Windows PowerShell：

```powershell
$env:SCP_LAB_SIM_PYTHON = "$PWD/.venv-sim/Scripts/python.exe"
uv run --no-sync python examples/ot2_simulation.py
```

## L3 移液功能与执行流程

`ot2-sim` 以 L3 接入方式开放 `ot2.liquid_transfer`，将移液封装为参数化的设备功能。在这一接入方式下，调用方指定来源孔、目标孔和体积，功能内部的操作顺序由后端预先定义。

OT-2 后端校验请求后，按照该 L3 功能预定义的“取枪头 → 吸液 → 排液 → 丢枪头”顺序生成执行程序。本例生成的移液代码为：

```python
pipette.pick_up_tip()
pipette.aspirate(50.0, labware['plate']['A1'])
pipette.dispense(50.0, labware['plate']['B1'])
pipette.drop_tip()
```

官方仿真器执行该程序，执行状态、操作日志及错误信息通过 SCP-Lab 返回调用方。

## 执行结果

[示例脚本](../../examples/ot2_simulation.py)通过本地 MCP 会话调用 `submit_execution` 开始任务，再轮询 `get_execution` 获取状态，直到执行结束。脚本打印执行状态，并把执行记录中的 `result` 显示为 `simulation`。

### 状态查询

任务执行过程中，`get_execution` 返回的执行记录 `data` 包含以下状态（节选）：

```json
{
  "status": "running",
  "result": {}
}
```

`running` 表示任务仍在执行，`result` 尚未包含最终结果。任务成功完成后，同一查询返回的 `status` 变为 `succeeded`，`result` 包含仿真记录。

### 示例脚本输出

`ot2_simulation.py` 在执行结束后打印最终结果。以下输出表示成功执行（节选）：

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

`status: succeeded` 表示生成的程序在官方仿真器中执行成功，完成依据是仿真运行日志；`physical_execution: false` 表示没有驱动物理设备。

### 保存和读取仿真记录

仿真结束后，输出中的 `simulation` 对象会保存为 `.scp-lab/runs/<仿真记录ID>.json`，其中包含生成程序、操作日志和执行前检查结果。仿真记录 ID 是 `simulation.run_id`，每次运行都会生成新值。

在仓库根目录运行以下命令，将 `SIMULATION_RUN_ID` 替换为本次输出的 `simulation.run_id`：

```bash
uv run --no-sync scp-lab run SIMULATION_RUN_ID
```

该命令读取已保存的记录。最外层的 `run_id` 则用于当前 MCP 会话中的 `get_execution` 查询。若设置了 `SCP_LAB_RUN_DIR`，记录会保存在该目录，读取时也需使用同一设置。

### 操作日志

`simulation.commands` 保存仿真器的操作日志。其中四条记录的 `text` 与移液代码中的四个操作对应（节选）：

```text
Picking up tip from A1 of Opentrons OT-2 96 Tip Rack 300 µL on slot 1
Aspirating 50.0 uL from A1 of NEST 96 Well Plate 200 µL Flat on slot 3 at 92.86 uL/sec
Dispensing 50.0 uL into B1 of NEST 96 Well Plate 200 µL Flat on slot 3 at 92.86 uL/sec
Dropping tip into Trash Bin on slot 12
```

日志显示，仿真器按顺序取枪头、从 A1 吸取 50 µL、向 B1 排出 50 µL，再丢弃枪头。完整生成程序保存在 `simulation.generated_code`，本次使用的 SDK 版本记录在 `simulation.sdk_version`，值为 `8.8.2`。

### 执行前检查

`simulation.validation` 保存 SCP-Lab 的执行前检查结果。本例的枪头用量和孔内预测体积（节选）：

```json
{
  "required_tips": 1,
  "predicted_wells": [
    {"location": "plate/A1", "volume_ul": 150.0},
    {"location": "plate/B1", "volume_ul": 50.0}
  ]
}
```

这次操作预计使用一个枪头；A1 从声明的 200 µL 减少到 150 µL，初始为空的 B1 增加到 50 µL。这些数值由声明的初始液量和转移参数计算，属于执行前预测。仿真日志用于确认程序能够在模拟环境中执行；真实移液量和液体行为仍需物理实验确认。

可以修改请求文件中 `arguments.parameters.volume_ul` 再次运行，对照生成程序、操作日志和预测体积的变化。更换来源孔时，也要在 `arguments.liquids` 中声明相应的初始液量。

本教程通过终端和 JSON 查看反馈。图形预览的使用方式见官方 [OT-2 App 可视化指南](https://docs.opentrons.com/ot-2/opentrons-app/protocol-viz/)。

要在其他 MCP 客户端中使用该后端，重新生成[本地客户端配置](clients.md)：

```bash
uv run --no-sync scp-lab mcp-config --output mcp-config.json
```

## 能力与设备布局

查看设备的完整描述，其中包含每项能力的输入与结果 schema：

```bash
uv run --no-sync scp-lab device ot2-sim
```

能力列表位于输出的 `capabilities` 数组中，名称和访问级别分别是 `capability_id` 和 `access_level`。在前面 `describe_device` 返回的 `descriptor` 上，只提取这两个字段：

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

标记为 `L3` 的八项是设备功能；`ot2.delay` 是辅助等待步骤，其 `access_level` 为 `null`，这里显示为 `-`。

本仿真后端支持单通道移液器。每次从一个孔向另一个孔转移液体，或执行一次混匀功能，都会使用新枪头。分液和汇液按以下方式执行：

| 功能 | 请求示例 | 执行顺序 |
| --- | --- | --- |
| 分液 | 从 A1 向 B1、B2 各分配 50 µL | 先从 A1 向 B1 转移 50 µL，再从 A1 向 B2 转移 50 µL |
| 汇液 | 从 A1、A2 各取 50 µL，汇入 B1 | 先从 A1 向 B1 转移 50 µL，再从 A2 向 B1 转移 50 µL |

使用温控、振荡等模块时，需要在 `setup` 中将孔板的位置设为相应模块。例如，[温控示例](../../examples/protocols/temperature_hold.json)将孔板的 `location` 设为温控模块的 ID `module`；仿真从“孔板已经位于温控模块上”的状态开始，不包含把孔板从其他位置搬到模块上的操作。

执行前检查会确认耗材是否受支持，以及移液体积是否在所选移液器的范围内。

独立的 `ot2-validation` 实例有十项 schema 校验动作，其参数和执行模式均与 `ot2-sim` 不同。

## 更多实验示例

除单次移液外，仓库还提供连续稀释、样品汇集，以及温控、振荡、温度循环和磁吸操作的仿真示例。每个文件都包含所需的设备布局和初始液量，并在 `steps` 中列出要执行的一项或多项操作。

| 输入文件 | 示例内容 |
| --- | --- |
| [serial_dilution.json](../../examples/protocols/serial_dilution.json) | 分配稀释液、连续转移并混匀 |
| [pooling.json](../../examples/protocols/pooling.json) | 汇集两个来源的液体、混匀并等待 |
| [temperature_hold.json](../../examples/protocols/temperature_hold.json) | 让温控模块在指定温度保持一段时间 |
| [heater_shaker.json](../../examples/protocols/heater_shaker.json) | 让振荡模块按指定转速运行一段时间 |
| [thermal_profile.json](../../examples/protocols/thermal_profile.json) | 按设定的温度、保持时间和循环次数运行热循环模块 |
| [magnetic_hold.json](../../examples/protocols/magnetic_hold.json) | 启动磁吸模块，保持指定时间后停止 |

以连续稀释为例：

```bash
# 检查输入参数和实验准备是否满足执行要求。
uv run --no-sync scp-lab validate examples/protocols/serial_dilution.json
# 生成可查看的 Python 程序。
uv run --no-sync scp-lab compile examples/protocols/serial_dilution.json -o build/serial_dilution.py
# 在官方仿真器中执行。
uv run --no-sync scp-lab simulate examples/protocols/serial_dilution.json
```

`validate` 会检查孔位是否有效、是否有两个耗材占用同一槽位、所需模块和枪头是否齐备，以及来源孔的液量是否足够完成转移。同时也会检查体积、温度等参数是否超出允许范围。

`simulate` 输出中的 `run_id` 可用于[读取保存的仿真记录](#保存和读取仿真记录)。

仓库提供[生成代码](../../examples/results/serial_dilution.py)和[官方仿真记录](../../examples/results/serial_dilution.simulation.json)，可直接查看完整示例。

<a id="ot-2-specific-tools"></a>
## OT-2 专用工具

本参考服务提供以下 OT-2 专用 MCP 工具，用于检查上述实验流程、生成程序和运行仿真：

| 工具 | 用途 |
| --- | --- |
| `capabilities` | 查询 OT-2 后端支持的操作、参数格式和耗材 |
| `validate_protocol` | 检查 OT-2 实验流程的参数、布局和液量 |
| `compile_protocol` | 将 OT-2 实验流程转换为 Python 程序 |
| `simulate_protocol` | 执行官方仿真，完成后返回仿真记录 |
| `invoke_capability` | 默认为单项 OT-2 操作生成程序；设置 `mode="simulate"` 可运行仿真 |
| `read_simulation_run` | 根据仿真记录 ID 读取已保存的结果 |

例如，通过 MCP 校验、生成并仿真连续稀释程序：

```bash
# 校验输入并生成程序。
uv run --no-sync python examples/mcp_client.py examples/protocols/serial_dilution.json
# 在校验和生成程序后，继续运行官方仿真。
uv run --no-sync python examples/mcp_client.py examples/protocols/serial_dilution.json --simulate
```

前面的[设备调用示例](../../examples/ot2_simulation.py)使用 `describe_device`、`submit_execution` 和 `get_execution` 完成能力查询、任务提交和状态查询。本节工具用于直接处理 OT-2 实验程序，返回格式和任务管理规则见[接口参考](device-access.md#错误与-schema)。

SDK 参考：[Opentrons 执行与仿真文档](https://docs.opentrons.com/python-api/reference/execute-simulate/)。
