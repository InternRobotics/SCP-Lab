# 应用与 Agent 接入

[English](../clients.md) · [文档目录](README.md) · [首页](../../README.zh-CN.md) · [入门教程](getting-started.md) · [设备接入](backends.md)

本指南介绍如何从应用或 Agent **调用**实验室能力。SCP-Lab 提供本地 MCP 服务，应用框架、智能体和实验逻辑由调用方选择。若需要把仪器或 SDK 的能力**提供给**调用方，请阅读[设备接入指南](backends.md)。

项目内置 45 个型号的接口定义，并为每个型号配置了离线校验实例，提供 89 项能力。无需连接真机，即可用它们[测试智能体的能力发现、请求构造和多步骤调用](#bundled-device-interface-environment)。

## 1. 连接支持 MCP 的应用

完成[基础安装](installation.md)后，在仓库根目录运行：

```bash
uv run --no-sync scp-lab mcp-config --output mcp-config.json
```

生成的文件包含一个 `mcpServers.scp-lab` 条目：

| 字段 | 含义 |
| --- | --- |
| `command` | 已安装 SCP-Lab 的 Python 解释器绝对路径 |
| `args` | `-m scp_lab.server` |
| `env` | 已配置的本地后端和仿真器环境设置 |

如果客户端接受 `mcpServers` 配置文件，将 `scp-lab` 条目合并到现有配置中。如果客户端通过界面分别填写字段，将命令、参数和环境变量填入本地 stdio 服务设置。保留已配置的其他 MCP 服务。

客户端会以子进程形式启动 SCP-Lab。本实现使用本地 **stdio**，不需要远程服务 URL 或 SCP 平台账号。应在运行客户端的电脑上生成配置；移动仓库或更换后端环境后，需要重新生成。此命令只写入配置文件，不会修改应用设置。

使用自己的实例时，先完成[设备配置](backends.md#configure-devices-with-an-existing-backend)，再用 `--devices-dir` 生成客户端条目。使用可选的 OT-2 后端时，先完成[仿真器安装](installation.md#ot-2-simulation)，再重新生成配置。

## 2. 发现并调用能力

### 获取工具列表

连接 SCP-Lab 后，通过 MCP 工具发现接口获取可用工具：

```python
tools = await client.list_tools()
for tool in tools.tools:
    print(tool.name, tool.description)
```

每项工具包含名称、用途说明和 `inputSchema`。智能体据此了解有哪些接口，以及调用时需要哪些参数。其中，通用设备工具包括：

| 工具 | 用途 |
| --- | --- |
| `list_devices` | 发现已配置的设备实例、执行模式和当前状态 |
| `describe_device` | 读取实例的能力、参数 schema、结果 schema 和能力描述版本 |
| `submit_execution` | 提交一次明确的能力请求，获取任务 ID |
| `get_execution` | 查询任务状态、进度、结果、错误和完成依据 |
| `get_device_state` | 读取可用性、占用情况及设备报告的观测 |
| `cancel_execution` | 在能力描述声明支持取消时，请求取消执行 |

### 查询已登记的设备

调用 `list_devices` 时传入空参数，即可获取全部已登记设备；如果指定 `device_class`，则只返回该类型的设备。

```python
from examples.device_client import call

devices = await call(client, "list_devices", {})
for device in devices:
    print(device["device_id"], device["display_name"],
          device["execution_mode"], sep=" | ")
```

默认配置的输出节选，依次为设备 ID、名称和执行模式：

```text
agilent_biotek_synergy_h1-validation | Agilent BioTek Synergy H1 (schema validation) | schema_validation
cytomat_6002-validation | Cytomat 6002 (schema validation) | schema_validation
demo-heater | Mock heater | mock
hamilton_star-validation | Hamilton STAR (schema validation) | schema_validation
ot2-sim | OT-2 official simulator | official_simulation
```

默认服务登记 48 个实例：45 个 `schema_validation` 离线校验实例、2 个 `mock` 加热器和 1 个 `official_simulation` OT-2 实例。未安装可选仿真环境时，OT-2 实例仍可发现，但状态报告不可用。

智能体结合实验需求、设备名称和执行模式选择候选设备，再查询其具体能力。本例选择查询结果中的 `demo-heater`，演示一次 mock 调用。

### 查询能力与参数格式

使用返回的设备 ID 调用 `describe_device`，读取能力列表及用途说明：

```python
device = next(item for item in devices if item["device_id"] == "demo-heater")
descriptor = await call(client, "describe_device", {"device_id": device["device_id"]})
for item in descriptor["capabilities"]:
    print(item["capability_id"], item["description"], sep=" | ")
```

此设备返回：

```text
demo_heater.hold | Timed runtime demonstration, no physical heating.
```

选取返回的 `demo_heater.hold`，读取其 `input_schema` 中的输入字段：

```python
capability = next(
    item for item in descriptor["capabilities"]
    if item["capability_id"] == "demo_heater.hold"
)
input_schema = capability["input_schema"]
print(list(input_schema["properties"]))
```

输出的字段名为：

```text
['target_celsius', 'duration_s']
```

本例将目标温度设为 37 °C、模拟持续时间设为 1 秒，因此填写 `target_celsius=37` 和 `duration_s=1`。参数类型、范围、单位和默认值由 `input_schema` 定义；详见[协议参考](device-access.md#units-and-defaults)。

### 提交请求

将设备 ID、能力 ID 和上述参数放入 `request`，调用 `submit_execution`：

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

返回的 `status` 为 `accepted`，`run_id` 是本次任务的 ID。可选字段 `expected_descriptor_revision` 用于检查提交时的能力描述版本是否仍与查询时一致。`idempotency_key` 用于重试同一次请求；新的操作应使用新的键。

### 查询状态与结果

请求被接受后，在同一个会话中使用任务 ID 调用 `get_execution`：

```python
record = await call(client, "get_execution", {"run_id": run_id})
print(record["status"])
print(record["result"])
```

每次查询都会返回当时的执行记录。任务处于 `accepted` 或 `running` 时，需要间隔一段时间继续查询；完成后从 `result` 读取结果。

此示例成功执行后的记录节选：

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

`demo-heater` 运行模拟计时流程；`measured_temperature` 为 `null`，表示没有实际温度测量。

## 3. 完整示例

| 示例 | 内容 |
| --- | --- |
| [quickstart.py](../../examples/quickstart.py) | 发现演示加热器、查询能力、提交请求并读取结果 |
| [01_device_call.py](../../examples/01_device_call.py) | 发现默认实例，校验部分设备型号的代表性请求 |
| [02_multi_device.py](../../examples/02_multi_device.py) | 按调用方定义的顺序，依次校验移液、培养和读板请求 |

会话建立、工具调用和轮询的辅助函数位于 [examples/device_client.py](../../examples/device_client.py)。这些脚本是普通 MCP 客户端；接入智能体时，可以由智能体根据设备描述选择能力并构造请求。

<a id="bundled-device-interface-environment"></a>
### 使用内置接口测试智能体

内置接口可作为智能体的基础离线调用环境。通过前面的 `list_devices` → `describe_device` → `submit_execution` → `get_execution` 流程，可以检查智能体能否找到所需设备、选择操作、按 schema 填写参数，并根据错误反馈修正请求。

从设备列表中筛选离线校验实例：

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

默认配置的输出为：

```text
{'devices': 45, 'capabilities': 89}
```

例如，可以给智能体以下任务，让它从发现设备开始选择接口：

```text
查询可用的离线校验设备，为 sample-plate 设计移液、培养、读板的调用顺序。
读取候选设备的能力描述，按 input_schema 构造并提交每一步请求。
如果请求被拒绝，根据错误信息修正；最后报告各步骤的校验结果。
```

这类调用返回的 `result.validated_command` 是通过 schema 检查的请求，`completion_evidence.kind` 为 `schema_validation`。可用于观察智能体如何选择接口、组织调用，并检查每次请求的格式。样品是否存在、板是否实际移动、实验是否有效，以及测量读数，都需要执行后端提供反馈。

已有示例可用于查看完整调用流程：

```bash
# 发现设备，并校验代表性的设备请求。
uv run --no-sync python examples/01_device_call.py
# 依次校验移液、培养和读板请求。
uv run --no-sync python examples/02_multi_device.py
```

请求保存在 [device_classes.json](../../examples/requests/device_classes.json)。多设备示例用同一个 `sample-plate` 标识关联请求，顺序由示例脚本指定；各次校验不模拟液量、样品位置或实验结果的变化。完整型号列表见[设备目录](devices.md#接口目录)。

### 发现不到内置接口时

先使用 `list_devices` 的空参数调用，避免 `device_class` 筛选隐藏其他类型。MCP 的 `list_tools` 返回通用工具；具体设备及其操作分别通过 `list_devices` 和 `describe_device` 查询。

检查客户端中 SCP-Lab 服务的 `command` 是否指向当前安装环境，以及设备目录设置是否正确。指定 `SCP_LAB_DEVICES_DIR` 或 `--devices-dir` 时，服务只加载该目录，替换默认集合。若要明确加载仓库内置实例，在仓库根目录生成配置：

```bash
uv run --no-sync scp-lab mcp-config --devices-dir ./src/scp_lab/data/devices --output mcp-config.json
```

将生成的 `scp-lab` 条目更新到客户端配置并重启该服务，再调用 `list_devices`。若要同时使用自有设备和部分内置接口，将所需的内置实例配置复制到自有设备目录，具体见[设备配置](backends.md#configure-devices-with-an-existing-backend)。

## 4. 处理执行结果

### 判断任务状态

调用 `get_execution` 后，根据执行记录的 `status` 决定下一步：

| `status` | 含义 | 调用方的处理 |
| --- | --- | --- |
| `accepted`、`running` | 请求已接受或正在执行 | 等待后继续查询，可读取 `progress` 了解进度 |
| `cancel_requested` | 已请求取消，后端尚未确认结果 | 继续查询，等待最终状态 |
| `succeeded` | 执行成功 | 读取 `result`，结合执行模式和完成依据解释结果 |
| `failed` | 执行失败 | 读取 `error.code`、`error.message` 和 `error.details`，排查原因 |
| `cancelled` | 后端已确认操作停止 | 按取消结果处理后续实验步骤 |
| `unknown` | 后端无法确认执行结果 | 核实设备及实验状态，再决定后续操作 |

查询到失败任务时，响应仍可为 `ok: true`，任务失败体现在 `data.status` 和 `data.error` 中。响应节选：

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

如果工具调用本身出错，例如任务 ID 不存在，MCP 响应会设置 `isError: true`。前面使用的 `call()` 辅助函数会抛出异常；成功时返回 `data`，因此通过 `record["status"]` 读取任务状态。完整响应格式见[协议参考](device-access.md#mcp-工具与消息)。

### 读取结果与完成依据

任务成功后，`result` 中的字段由该能力的 `result_schema` 定义。还应读取 `execution_mode` 和 `completion_evidence`，了解这次执行完成了什么检查或操作：

```python
print(record["execution_mode"])
print(record["completion_evidence"]["kind"])
```

前面的加热器示例返回：

```text
mock
mock_trace
```

这表示 mock 计时流程已完成。OT-2 官方仿真则返回 `official_simulation` 和 `official_simulator_runlog`，表示程序通过了软件仿真。真机执行的完成条件和反馈由接入后端声明；各模式的具体含义见[完成依据](device-access.md#completion-evidence)。

### 取消、重试与超时

- 设备描述中的 `cancellation_supported` 为 `true` 时，可以调用 `cancel_execution`。返回 `cancel_requested` 后继续查询；最终可能是 `cancelled`，也可能是操作已完成时的 `succeeded`。
- 如果提交后没有收到响应，重试时使用原来的请求和 `idempotency_key`，避免重复创建任务。要执行新的操作，使用新的键；用旧键提交不同参数会被拒绝。
- 等待超时只表示还没等到结果，设备可能仍在执行。保持当前连接，用原来的 `run_id` 继续查询。如果状态为 `unknown`，先查看设备日志或实际状态，确认操作执行到哪一步，再决定是否重新提交。

当前版本的任务记录只保存在正在运行的 SCP-Lab 服务中。服务关闭或重启后，原来的 `run_id` 无法继续查询，旧的 `idempotency_key` 也无法防止重复提交。多个独立启动的服务各自记录设备是否忙碌，因此同一台真实设备应由一个服务统一控制。详见[重复提交与服务运行范围](device-access.md#幂等性与会话范围)。

以上处理方式适用于通用设备工具。[OT-2 专用工具](ot2-examples.md#ot-2-specific-tools)的返回格式及仿真记录说明见[协议参考](device-access.md#错误与-schema)。
