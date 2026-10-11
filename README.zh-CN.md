# SCP-Lab

**通过统一接口发现实验室能力、提交任务并获取执行反馈。**

[English](README.md) · [快速开始](docs/zh-CN/getting-started.md) · [应用接入](docs/zh-CN/clients.md) · [设备接入](docs/zh-CN/backends.md) · [完整文档](docs/zh-CN/README.md)

技术报告（含附录）：[下载 PDF](docs/report/SCP-Lab-Technical-Report.pdf?raw=true) · [GitHub 预览](docs/report/SCP-Lab-Technical-Report.pdf)

SCP-Lab 是 [Science Context Protocol（SCP）](https://github.com/InternScience/scp) 面向自主实验室的扩展。科学智能体通过统一接口发现实验能力、提交任务，设施侧的后端负责控制设备或岛台执行操作，并返回执行状态与实验结果。智能体基于这些反馈优化后续实验方案。

![SCP-Lab 概览：通过统一接口连接科学智能体、实验设备与实验依据。](docs/assets/scp-lab-teaser.png)

## 工作方式

智能体、SCP-Lab 和设施后端的分工如下：

| 角色 | 职责 |
| --- | --- |
| 科学智能体 | 制定实验方案，发现设施能力并发起任务，分析反馈、优化后续实验 |
| SCP-Lab | 统一设备与能力的登记和发现，规范能力描述与控制范围，提供任务提交、状态、结果和完成依据的交互接口 |
| 设施执行后端 | 校验请求与本地执行条件，控制设备或岛台执行实验操作，并返回执行状态、结果与完成依据 |

```mermaid
flowchart LR
    Agent["科学智能体"] -->|实验任务| SCP["SCP-Lab"]
    SCP -->|任务请求| Backend["设施执行后端"]
    Backend -->|状态、结果与完成依据| SCP
    SCP -->|执行反馈| Agent
```

接入方在登记设备时明确其能力，包括支持的操作、参数和完成标准，并关联对应的执行后端。智能体通过 SCP-Lab 发现和查询这些能力，了解设施能够执行哪些操作、允许调整哪些参数，据此选择合适的设施、设计实验方案并提交任务。执行时，后端将状态、结果和完成依据通过 SCP-Lab 返回智能体，供其评估实验结果并调整后续方案。

SCP-Lab 用 L1–L5 五个访问级别描述设施开放的控制范围，从完整工作流到执行器动作。这让智能体能够根据实验需求，选择复用既定流程或组织更细的操作，也让控制粒度不同的设施采用一致的方式接入。接入方可以据此选择任务粒度与编排方式。

SCP-Lab 提供 MCP 兼容接口，使现有 MCP 客户端能够接入设施能力。访问级别、执行反馈与 MCP 兼容接口的细节见[设计说明](docs/zh-CN/design.md)。

## 安装

准备好 Git 和 [uv](https://docs.astral.sh/uv/getting-started/installation/)，运行：

```bash
git clone https://github.com/InternRobotics/SCP-Lab.git scp-lab
cd scp-lab
uv sync --frozen --python 3.12 --extra mcp
```

命令会在 `.venv` 中安装 SCP-Lab 及 MCP 接入依赖。已有源码时，直接在仓库根目录运行最后一条命令即可。环境准备、安装验证和常见问题见[安装指南](docs/zh-CN/installation.md)。

安装完成后，可以按需选择教程，或直接进入接入指南。

## 教程

| 教程 | 体验内容 |
| --- | --- |
| [入门：第一次设备调用](docs/zh-CN/getting-started.md) | 发现演示设备、提交任务并理解执行反馈 |
| [进阶：OT-2 仿真](docs/zh-CN/ot2-examples.md) | 从移液请求生成代码，在官方仿真器中执行并读取结果 |

## 接入指南

| 你的目标 | 指南 | 完成后得到什么 |
| --- | --- | --- |
| 从应用或 Agent 调用设备 | [应用接入](docs/zh-CN/clients.md) | 通过 MCP 发现能力、提交请求和读取结果 |
| 注册设备实例 | [设备配置](docs/zh-CN/backends.md#configure-devices-with-an-existing-backend) | 使用已有适配器，为每个实例保存一份配置 |
| 封装 SDK 或实验室服务 | [后端开发](docs/zh-CN/backends.md#develop-an-adapter-for-a-new-sdk-or-api) | 提供能力定义、返回执行反馈的可复用适配器 |

## 设备接口与示例

| 内容 | 用途 |
| --- | --- |
| 基于本地 MCP stdio 的设备访问 API | 发现设备、读取能力、提交任务、查询执行与设备状态，以及后端支持的取消操作 |
| 离线接口目录 | 45 个设备型号、89 个动作定义的请求校验 |
| OT-2 后端 | 代码生成与官方仿真，仿真器需单独安装 |
| Mock 设备与适配器模板 | 应用接入、执行生命周期和多实例配置示例 |

[型号定义](src/scp_lab/adapters/README.zh-CN.md)按设备类别独立保存，通过实例配置即可由 MCP 调用；这些文件同时也是[发布新设备接口](docs/zh-CN/backends.md#add-a-model-for-offline-validation)的参考样例。

内置后端在软件中运行，连接物理设备需要实现硬件适配器。

## 继续阅读

- [用户指南](docs/zh-CN/README.md)：教程、接入步骤与参考页面。
- [示例目录](examples/README.zh-CN.md)：设备调用、多设备序列、生命周期处理与自定义后端。
- [协议参考](docs/zh-CN/device-access.md)与 [JSON Schema](schemas/README.zh-CN.md)：消息、单位、默认值、生命周期和完成依据。
- [贡献指南](CONTRIBUTING.zh-CN.md)：开发环境与检查方法。
