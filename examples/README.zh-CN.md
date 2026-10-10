# SCP-Lab 示例

[English](README.md) · [首页](../README.zh-CN.md) · [文档目录](../docs/zh-CN/README.md) · [安装](../docs/zh-CN/installation.md) · [客户端接入](../docs/zh-CN/clients.md) · [设备接入](../docs/zh-CN/backends.md)

完成安装后，在仓库根目录运行这些示例。它们是普通 Python MCP 客户端，无需模型 API key。每个客户端启动自己的本地服务，并在提交和查询期间保持会话。

## 从一次调用开始

```bash
uv run --no-sync python examples/quickstart.py
```

[quickstart.py](quickstart.py) 发现演示加热器、读取能力、提交请求并获取执行记录。修改 `request.arguments` 可以尝试不同参数。共同的 [device_client.py](device_client.py) 负责 MCP 连接和响应处理。

## 选择一个使用场景

| 命令 | 预期行为 |
| --- | --- |
| `uv run --no-sync python examples/ot2_simulation.py` | 通过 `ot2-sim` 执行移液，需要[可选仿真环境](../docs/zh-CN/ot2-examples.md) |
| `uv run --no-sync python examples/01_device_call.py` | 发现本地实例，校验代表性的设备请求 |
| `uv run --no-sync python examples/02_multi_device.py` | 按调用方定义的序列调用移液、培养和读板接口 |
| `uv run --no-sync python examples/03_runtime.py` | 查看进度、拒绝忙碌设备上的请求、对重复请求去重、取消执行并处理注入的失败 |
| `uv run --no-sync python examples/04_custom_backend.py` | 通过同一个适配器加载两份酶标仪配置，分别调用并查看独立设置和观测 |

`01_device_call.py --simulate` 会在目录调用之后额外调用 OT-2 仿真器。只运行 OT-2 时，使用 [ot2_simulation.py](ot2_simulation.py)。

## 理解反馈

- 目录示例返回 `schema_validation` 完成依据，检查输入 schema，不调用对应 SDK。
- 多设备示例依次提交转移 50 uL、在 37 °C 孵育 30 分钟和读取吸光度的请求，在请求之间共享 `sample-plate` 标识。流程顺序由调用方定义，不自动转移板或核实样品位置。
- 加热器示例使用软件计时器，演示执行行为，不模拟热力学。
- `adapters/example_lab/plate_reader/backend.py` 中的酶标仪模板返回 `synthetic=true`。`04_custom_backend.py` 通过该适配器加载 [devices/](devices) 中的持久化 JSON。两个实例具有独立设置；观测报告 `last_plate_id`，同时包含 `kind="simulated"`、来源和时间戳。客户端启动自己的服务：修改 Python 调用改变实验，修改 JSON 则改变下次启动时配置的实例。
- OT-2 示例返回 `official_simulator_runlog` 完成依据，且 `physical_execution=false`。

各类结果的含义见[设备目录与执行模式](../docs/zh-CN/devices.md)。

## 请求文件与后端模板

| 文件 | 用途 |
| --- | --- |
| [requests/device_classes.json](requests/device_classes.json) | 设备调用的完整代表性请求 |
| [requests/ot2_execution.json](requests/ot2_execution.json) | `ot2-sim` 的布局、初始液体和移液参数 |
| [adapters/](adapters) | 可独立安装的酶标仪软件包，分别保存型号 JSON、schema 加载器、后端和工厂 |
| [models/example_heater.json](models/example_heater.json) | [离线接入教程](../docs/zh-CN/backends.md#add-a-model-for-offline-validation)使用的独立型号文件 |
| [protocols/](protocols/) | OT-2 编译器使用的多步骤实验输入 |

`mcp_client.py` 和 `call_tool.py` 演示 OT-2 专用辅助工具，其格式见 [OT-2 指南](../docs/zh-CN/ot2-examples.md)。一个示例服务返回的任务 ID 不能从另一个服务进程查询。

除自定义后端示例外，其他示例使用内置默认设备集合。如果设置 `SCP_LAB_DEVICES_DIR` 选择了本地目录，需确保该目录包含示例所引用的实例 ID。
