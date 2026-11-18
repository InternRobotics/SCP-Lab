# 用 SCP-Lab 接入实验室仪器

[English](../http-instruments.md) · [后端接入指南](backends.md)

通过 SCP-Lab 采集图像和测量值、在现场辨认 Opentrons 工作站，或查询奔曜调度器状态。每台实例都通过同一个 SCP-Lab MCP 接口发布可调用的操作。软件测试使用本地设备协议测试服务，真机验收待现场完成。

| 设备或服务 | SCP-Lab 能力 | 调用成功的依据 |
| --- | --- | --- |
| Opentrons OT-2 / Flex | `opentrons.get_rail_lights` | 机器人控制器返回工作区照明灯的开关状态。 |
| Opentrons OT-2 / Flex | `opentrons.set_rail_lights` | 设置后，单独发起的读取返回目标状态。现场人员可目视确认。 |
| 奔曜 Bioyond Studio LIMS | `bioyond.get_scheduler_status` | 服务返回成功，并给出调度器状态，例如 `Stop`。各台仪器另有自己的运行状态。 |

SCP-Lab 适配器调用 [Opentrons HTTP API](https://docs.opentrons.com/http/api_reference.html) v2 的照明接口和奔曜 Bioyond Studio LIMS 的状态查询接口。奔曜现场服务地址、接口版本和凭据需与设施方核对。

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

## 测量与成像设备

下表每一款都有独立的 SCP-Lab 实例配置和可执行的采集操作。把现场型号对应的配置文件复制到 `lab-devices/`，再替换示例连接信息。型号链接指向项目方或厂家的接口定义。

| 型号及接口依据 | 实例配置 | SCP-Lab 能力 | 实际返回 |
| --- | --- | --- | --- |
| [OpenFlexure Microscope](https://openflexure.gitlab.io/openflexure-microscope-server/http/openapi.json) | [openflexure_microscope.json](../../examples/measurement-devices/openflexure_microscope.json) | `openflexure_microscope.snapshot` | JPEG 预览图、字节数、SHA-256 和服务器本地文件 URI |
| [EEZ Bench Box 3 (BB3)](https://www.envox.eu/eez-bench-box-3/bb3-scpi-reference-manual/5-subsystem-command-reference/) | [eez_bb3.json](../../examples/measurement-devices/eez_bb3.json) | `eez_bb3.read_voltage` | 指定通道感测端的实测电压（V） |
| [Red Pitaya STEMlab 125-14](https://redpitaya.readthedocs.io/en/latest/appsFeatures/examples/analog/ana-1-read_analog_inputs.html) | [stemlab_125_14.json](../../examples/measurement-devices/stemlab_125_14.json) | `stemlab_125_14.read_voltage` | AIN0–AIN3 中指定慢速模拟输入的电压（V） |
| [Tinkerforge Load Cell Bricklet 2.0](https://github.com/Tinkerforge/generators/blob/master/configs/bricklet_load_cell_v2_config.py) | [load_cell_v2.json](../../examples/measurement-devices/load_cell_v2.json) | `load_cell_v2.read_weight` | 外接已校准称重传感器的读数（g） |
| [Tinkerforge CO2 Bricklet 2.0](https://github.com/Tinkerforge/generators/blob/master/configs/bricklet_co2_v2_config.py) | [co2_v2.json](../../examples/measurement-devices/co2_v2.json) | `co2_v2.read_co2` | 环境 CO₂ 浓度（ppm） |
| [Tinkerforge Color Bricklet 2.0](https://github.com/Tinkerforge/generators/blob/master/configs/bricklet_color_v2_config.py) | [color_v2.json](../../examples/measurement-devices/color_v2.json) | `color_v2.read_color` | 红、绿、蓝及无滤光四路光电计数 |
| [Tinkerforge Humidity Bricklet 2.0](https://github.com/Tinkerforge/generators/blob/master/configs/bricklet_humidity_v2_config.py) | [humidity_v2.json](../../examples/measurement-devices/humidity_v2.json) | `humidity_v2.read_humidity` | 相对湿度（%RH） |

- **显微镜。** 选择提供 `GET /camera/snapshot` 的 OpenFlexure 服务（v3 API），将 `output_dir` 设为 SCP-Lab 主机上已存在且可写的绝对路径。每次调用生成一张新图，可在主机上打开，与显微镜实时画面对照。
- **电学测量。** 开启仪器的以太网 SCPI 服务。BB3 选择已安装且支持测压的通道；STEMlab 选择扩展接口上的慢速模拟输入。用仪表显示值或参考电压表核对回读结果。
- **Bricklet 测量。** 这四款开源硬件模块经 Brick 主控和 Brick Daemon 或兼容网关连接。在 SCP-Lab 环境执行 `uv pip install --python .venv/bin/python -e './examples/adapters[bricklets]'` 安装可选驱动。填写网关地址、端口和 Brick Viewer 中各模块自己的 UID。示例适用于允许免鉴权绑定连接的网关。可用 Brick Viewer 核对读数，称重还需用已知质量核对外接传感器。

例如，把以下参数提交给 SCP-Lab 即可读取已配置的称重模块，再用返回的运行 ID 查询结果。七个采集操作的 `arguments` 均为空对象。

```json
{"request":{"device_id":"load_cell_v2","capability_id":"load_cell_v2.read_weight","arguments":{}}}
```

## 现场验收

检查实例是否注册，再生成 MCP 客户端配置。

```bash
uv run --no-sync scp-lab check --devices-dir lab-devices
uv run --no-sync scp-lab mcp-config --devices-dir lab-devices -o mcp-config.json
```

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
