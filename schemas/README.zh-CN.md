# JSON Schema

[English](README.md) · [首页](../README.zh-CN.md) · [文档目录](../docs/zh-CN/README.md) · [协议参考](../docs/zh-CN/device-access.md)

## SCP-Lab 通用设备访问格式

| 文件 | 对象 |
| --- | --- |
| [device-descriptor.schema.json](device-descriptor.schema.json) | 静态身份、能力、schema 与执行模式声明 |
| [device-state.schema.json](device-state.schema.json) | 动态可用性、占用和可选观测 |
| [execution-request.schema.json](execution-request.schema.json) | 面向一个设备能力的请求 |
| [execution-record.schema.json](execution-record.schema.json) | 请求状态、生效参数、结果、错误和完成依据 |

各项能力的 `input_schema`、`result_schema`，以及设备可选的 `state_schema`，定义设备自己的字段。通过 `describe_device` 获取这些定义；通用请求 schema 不规定所有设备的实验参数。

通用 schema 同时以 MCP 资源形式发布，路径分别为 `scp-lab://schemas/device-descriptor`、`scp-lab://schemas/device-state`、`scp-lab://schemas/execution-request` 和 `scp-lab://schemas/execution-record`。

## 参考服务的部署配置

[device-config.schema.json](device-config.schema.json) 定义一份持久化设备实例配置。后端负责校验自身的 `connection` 和 `options` 字段。这是本地部署格式，与 SCP-Lab 对外消息分开；其他协议实现可以采用自己的配置存储方式。详见[设备接入](../docs/zh-CN/backends.md)。

## 适配器型号定义

[device-model.schema.json](device-model.schema.json)定义独立保存的型号文件，包含 `model_id`、`device_class`、`display_name`、`capabilities` 和可选的 `state_schema`。每项能力使用共同的输入与结果 schema 结构。这是适配器的开发格式；客户端通过 `describe_device` 获取能力，适配器也可以通过代码生成 schema。

内置定义保存在 [adapters/<family>/models/](../src/scp_lab/adapters)，实例通过离线后端的 `options.model_resource` 或 `options.model_file` 选择文件。完整示例见[添加型号](../docs/zh-CN/backends.md#add-a-model-for-offline-validation)。

## OT-2 专属格式

| 文件 | 范围 |
| --- | --- |
| [protocol.schema.json](protocol.schema.json) | OT-2 编译器使用的多步骤实验输入 |
| [ot2-capabilities.json](ot2-capabilities.json) | 已实现的 OT-2 编译与仿真能力目录 |

这里的“protocol”表示该后端使用的实验流程，`protocol.schema.json` 不是所有 SCP-Lab 设备的通用输入格式。详见 [OT-2 示例](../docs/zh-CN/ot2-examples.md)。

通过 `uv run --no-sync python scripts/export_schemas.py` 重新生成这些文件，开发说明见[贡献指南](../CONTRIBUTING.zh-CN.md)。
