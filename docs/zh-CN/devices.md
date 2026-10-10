# 设备目录与执行模式

[English](../devices.md) · [文档目录](README.md) · [首页](../../README.zh-CN.md) · [入门教程](getting-started.md) · [设备接入](backends.md)

本指南介绍可用接口及对应示例。**型号（model）**表示一类仪器，**实例（instance）**表示本地服务中已配置的一个后端对象。同一型号的不同实例可以发布不同能力。

## 选择执行后端

根据希望检查的内容选择实例，通过其 `execution_mode` 和完成依据理解结果。

| 实例 | 执行模式 | 成功调用表示什么 |
| --- | --- | --- |
| `demo-heater`、`demo-heater-fault` | `mock` | 软件演示完成，或报告配置好的取消、失败行为 |
| `ot2-sim` | `official_simulation` | 生成的代码在可选 Opentrons 仿真器中执行完成 |
| 以 `-validation` 结尾的实例 | `schema_validation` | 请求符合已发布的参数和资源绑定 schema |
| 自定义后端示例加载的 `reader-01`、`reader-02` | `mock` | 演示 SDK 返回明确标记为合成数据的读数 |
| 自行注册的实例 | 由后端声明 | 满足该集成发布的完成条件，并返回相应依据 |

默认服务使用与本地设备相同的加载器，读取 [48 份设备 JSON 配置](../../src/scp_lab/data/devices)：45 个离线校验实例、一个 OT-2 仿真实例和两个演示加热器。未配置仿真环境时，仿真实例报告不可用。内置后端不连接真实设备。通过 `--devices-dir` 或 `SCP_LAB_DEVICES_DIR` 选择目录后，该目录会替代默认设备选择。添加实例只需新增 JSON 文件，无需修改型号目录。

## 查看和调用接口

```bash
uv run --no-sync scp-lab devices
uv run --no-sync scp-lab device agilent_biotek_synergy_h1-validation
uv run --no-sync python examples/01_device_call.py
```

最后一条命令通过 MCP 提交部分内置设备型号的代表性请求。完整请求见 [device_classes.json](../../examples/requests/device_classes.json)。

应用应通过 `list_devices` 和 `describe_device` 发现接口，不能仅凭型号名称推断已安装某个驱动。静态描述包含该实例实际发布的能力和 schema，当前可用性则由动态状态报告。

## 接口目录

目录包含 45 个型号、89 个动作定义：

| 类别 | 型号数量 |
| --- | ---: |
| 酶标仪 | 12 |
| 存储设备 / 培养箱 | 8 |
| 移液工作站 | 6 |
| 加热振荡器 | 5 |
| 热循环仪 | 3 |
| 离心机 | 2 |
| 封膜机 / 揭膜机 | 2 |
| 温控设备 | 2 |
| 菌落挑选设备 | 1 |
| 手套箱 | 1 |
| 洗板机 | 1 |
| 试剂分液器 | 1 |
| 倾斜设备 | 1 |

离线校验后端发布各设备接口的参数名称、范围、枚举和条件约束，可用于在接入硬件前开发能力发现和请求构造。资源绑定是调用方提供的引用，后端检查其结构；物理样品位置和测量结果需要设备反馈。

型号定义保存在 [adapters/](../../src/scp_lab/adapters) 下，按设备类别组织。离线后端加载实例配置指定的打包资源或本地文件，记录定义的来源与 SHA-256 哈希。

## OT-2 仿真

[安装并运行 OT-2 仿真器](ot2-examples.md)，可以体验设备代码的生成与执行。`ot2-sim` 发布九项已实现能力；独立的 `ot2-validation` 发布十项接口定义，二者 schema 不同。调用前应读取目标实例的描述，不能仅凭能力名称互相套用参数。

## 接入设备

按[设备接入指南](backends.md)封装 SDK、仿真器或已有实验室服务。自定义后端可以发布更多能力或新的设备类别，同时继续使用相同的发现、提交和反馈工具。
