# 添加离线型号定义

[English](../models.md) · [用户指南](README.md) · [设备接入](backends.md) · [首页](../../README.zh-CN.md)

本教程通过一份型号定义和一份实例配置，发布可发现、可校验的设备接口。先完成[基础安装](installation.md)，以下命令均在仓库根目录运行。

<a id="add-a-model-for-offline-validation"></a>
## 添加型号定义，提供离线校验

创建 `lab-models/` 和 `lab-devices/` 目录，分别保存型号定义与实例配置，再通过已有离线后端加载型号。可以从 [45 个现有型号定义](../../src/scp_lab/adapters)开始，也可以将 [example_heater.json](../../examples/models/example_heater.json) 保存为 `lab-models/example_heater.json`。型号文件应放在实例配置目录之外。

这个示例发布 `example_heater.hold`，完整定义如下：

```json
{
  "schema_version": "scp-lab.device-model.v0.1",
  "model_id": "example_heater",
  "device_class": "temperature_controller",
  "display_name": "Example heater interface",
  "capabilities": [
    {
      "capability_id": "example_heater.hold",
      "description": "Validate a requested temperature and duration.",
      "input_schema": {
        "type": "object",
        "properties": {
          "target_celsius": {"type": "number", "minimum": 20, "maximum": 95, "x-scp-unit": "degC"},
          "duration_s": {"type": "number", "exclusiveMinimum": 0, "x-scp-unit": "s"}
        },
        "required": ["target_celsius", "duration_s"],
        "additionalProperties": false
      },
      "result_schema": {
        "type": "object",
        "required": ["validated_command", "source", "limitations"],
        "properties": {
          "validated_command": {"type": "object"},
          "source": {"type": "object"},
          "limitations": {"type": "array", "items": {"type": "string"}}
        }
      },
      "completion_criteria": "The declared parameter schema accepts the request.",
      "access_level": "L3"
    }
  ]
}
```

这些示例范围用于说明离线接口。实际接入时，根据设备接口确定参数名称、范围、单位和必填项。不同能力可以使用不同的参数结构，`parameters` 和 `bindings` 并非必需的外层字段。[型号文件 schema](../../schemas/device-model.schema.json)定义外层格式；`capabilities` 中的每个条目使用与 `describe_device` 发布内容相同的 `Capability` 结构。

另外保存实例配置 `lab-devices/heater-01.json`，把下面的绝对路径替换为已保存型号文件的位置：

```json
{
  "device_id": "heater-01",
  "backend": "scp_lab.adapters.offline:create_backend",
  "options": {"model_file": "/absolute/path/to/lab-models/example_heater.json"}
}
```

本例将能力定义保存在本机的 `lab-models/` 中，因此使用 `model_file` 告诉后端读取哪个文件；填写 SCP-Lab 服务所在机器上的绝对路径即可。如果定义随 Python 包安装，则改用 `model_resource`，两种方式的选择见[能力定义文件的位置](backends.md#model-definition-location)。

所选实例目录中的每份 JSON 都会被当作实例配置，因此能力定义保存在 `lab-models/`，实例配置保存在 `lab-devices/`。

检查已配置的接口并生成客户端配置：

```bash
uv run --no-sync scp-lab device heater-01 --devices-dir ./lab-devices
uv run --no-sync scp-lab check --devices-dir ./lab-devices
uv run --no-sync scp-lab mcp-config --devices-dir ./lab-devices --output mcp-config.json
```

按照[应用指南](clients.md)应用配置并重启服务，再提交以下请求：

```json
{
  "request": {
    "device_id": "heater-01",
    "capability_id": "example_heater.hold",
    "arguments": {"target_celsius": 37, "duration_s": 60}
  }
}
```

任务检查这些值后立即返回，不会等待 60 秒或进行加热。离线后端返回 `validated_command`、`source` 和 `limitations`，因此型号文件应声明这个校验报告的结果 schema 和完成条件。该后端使用 `defaults_policy="not_applied"`。需要解析默认值、返回其他结果或增加专属检查时，可以提供自己的后端。

向仓库贡献内置型号时，将定义放入 `src/scp_lab/adapters/<family>/models/<model_id>.json`，新增一份引用其包资源的实例配置，并提供代表性请求。新类别需增加 `__init__.py`，使文件所在目录成为可导入的软件包。运行 `scp-lab check` 并验证调用。

## 文件之间的关系

[内置适配器](../../src/scp_lab/adapters)按设备类别组织，每个型号在独立文件中维护。

```text
src/scp_lab/
├── backend.py                     # 共同后端接口与基础 schema 校验
├── adapters/
│   ├── schemas.py                 # 读取并检查一个型号定义
│   ├── offline.py                 # 可复用的离线校验后端与工厂
│   ├── plate_reader/models/
│   │   ├── agilent_biotek_synergy_h1.json
│   │   └── ...
│   ├── liquid/
│   │   ├── models/ot2.json         # OT-2 离线接口定义
│   │   ├── ot2_schemas.py          # 编译与仿真的能力 schema
│   │   └── ot2.py                 # 官方仿真后端与工厂
│   └── heater/
│       ├── models/demo_heater.json
│       ├── schemas.py
│       └── backend.py
└── data/devices/                   # 每台实例一份保存的配置
```

45 个离线型号共用后端实现，分别使用自己的 schema。需要生成 schema、增加专属检查或调用 SDK 时，可以在对应类别下增加 `schemas.py` 或 `backend.py`，也可以将适配器放在独立安装的软件包中。声明式型号共用离线工厂函数，通过独立 JSON 定义各自的能力。
