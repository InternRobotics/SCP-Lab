# 接入 Opentrons 工作站或奔曜 Bioyond Studio 调度器

[English](../http-instruments.md) · [后端接入指南](backends.md)

这两个可选适配器分别用于在现场辨认 OT-2 或 Flex，以及查询奔曜 Bioyond Studio 的调度状态。它们会调用配置中指定的 HTTP 服务。自动化测试已用本地 HTTP 测试服务核对请求和响应，真机验收待现场完成。

| 设备或服务 | SCP-Lab 能力 | 调用成功的依据 |
| --- | --- | --- |
| Opentrons OT-2 / Flex | `opentrons.get_rail_lights` | 机器人控制器返回工作区照明灯的开关状态。 |
| Opentrons OT-2 / Flex | `opentrons.set_rail_lights` | 设置后，单独发起的读取返回目标状态。现场人员可目视确认。 |
| 奔曜 Bioyond Studio LIMS | `bioyond.get_scheduler_status` | 服务返回成功，并给出调度器状态，例如 `Stop`。各台仪器另有自己的运行状态。 |

照明控制使用 [Opentrons HTTP API](https://docs.opentrons.com/http/api_reference.html) 的版本 2。奔曜接口依据 Uni-Lab-OS 公开的[调度器客户端](https://github.com/deepmodeling/Uni-Lab-OS/blob/43923ec9473e2f6d33d3ca1ebca4bf4d507e06b2/unilabos/devices/workstation/bioyond_studio/bioyond_rpc.py#L1008-L1023)和 [JSON 请求实现](https://github.com/deepmodeling/Uni-Lab-OS/blob/43923ec9473e2f6d33d3ca1ebca4bf4d507e06b2/unilabos/device_comms/rpc.py)。请与现场 Bioyond Studio 管理人员核对 LIMS 接口版本。

## 配置现场实例

完成[基础安装](installation.md)后，在 SCP-Lab 仓库根目录运行以下命令。

```bash
uv pip install --python .venv/bin/python --no-deps -e examples/adapters
mkdir -p lab-devices
```

每项现场服务单独保存一个 JSON 文件，将示例地址替换为实际值。OT-2 或 Flex 实例保存为 `lab-devices/robot-01.json`，其中填写机器人服务地址，常用端口为 31950。

```json
{
  "device_id": "robot-01",
  "backend": "example_lab.opentrons.backend:create_backend",
  "connection": {"base_url": "http://robot-01.example.invalid:31950"}
}
```

奔曜实例保存为 `lab-devices/studio-01.json`。填写服务地址，把 API 密钥放在本地文本文件中，并配置其绝对路径。SCP-Lab 服务进程在调用该能力时读取文件。

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

检查实例是否注册，再生成 MCP 客户端配置。

```bash
uv run --no-sync scp-lab check --devices-dir lab-devices
uv run --no-sync scp-lab mcp-config --devices-dir lab-devices -o mcp-config.json
```

## 现场验收

让 MCP 客户端加载生成的配置，用实例 ID 调用 `describe_device`。这一步读取本地能力定义。要实际访问设备服务，用下面任一参数调用 `submit_execution`，再在同一个 MCP 会话中用返回的 `run_id` 调用 `get_execution`，直到任务结束。

```json
{"request":{"device_id":"robot-01","capability_id":"opentrons.get_rail_lights","arguments":{}}}
```

```json
{"request":{"device_id":"studio-01","capability_id":"bioyond.get_scheduler_status","arguments":{}}}
```

验收照明时先记录原始 `result.on`，再切换到相反状态。目视确认后恢复原值。下面的调用会**开灯**。

```json
{"request":{"device_id":"robot-01","capability_id":"opentrons.set_rail_lights","arguments":{"on":true}}}
```

成功记录的 `completion_evidence.kind` 为 `device_reported`。奔曜可将 `result.schedulerStatus` 与 Studio 界面的调度状态核对。照明写入若丢失应答或无法读回，会返回 `unknown`，请在重试前核对现场状态。若成功读回的值与目标不一致，则返回 `failed` 并附上读到的值。

## 下一台设备需要哪些资料

记录型号、已装软件版本、控制接口归现场调度系统还是设备本身，以及现场希望先开放的一个操作。向接口负责人索取对应版本的 API 文档或 SDK、鉴权方式、一次成功和一次失败的返回样例，并约定怎样判断操作完成。用这些资料编写能力定义和适配器，再配置有独立 ID 的实例，安排现场验收。真实地址和凭据保存在本地。
