# 参与 SCP-Lab 开发

[English](CONTRIBUTING.md) · [首页](README.zh-CN.md) · [文档目录](docs/zh-CN/README.md) · [协议参考](docs/zh-CN/device-access.md) · [设备接入](docs/zh-CN/backends.md)

可以从协议定义、客户端示例、设备适配器或校验功能等方面参与。设备接入可从[后端模板](examples/adapters/example_lab/plate_reader/backend.py)开始，并说明适配器实际提供的执行模式和完成依据。

## 开发环境

在仓库根目录运行：

```bash
uv sync --frozen --python 3.12 --extra mcp --extra dev
uv run --no-sync ruff check src tests examples scripts
uv run --no-sync ruff format --check src tests examples scripts
uv run --no-sync scp-lab check
uv run --no-sync pytest -q
```

若需运行官方仿真测试，先安装 [OT-2 环境](docs/zh-CN/installation.md#ot-2-simulation)，并在运行 pytest 前设置 `SCP_LAB_SIM_PYTHON`。该可选环境不可用时，仿真测试会跳过。

## 生成文件

公开 schema 从校验模型导出。修改模型后重新生成：

```bash
uv run --no-sync python scripts/export_schemas.py
```

### 设备定义

每个型号的定义与适配器一起保存在 [src/scp_lab/adapters/](src/scp_lab/adapters) 下，按设备类别组织。型号 JSON 声明标识和能力，包括输入/结果 schema 与完成标准。离线后端为每个实例加载一份定义，记录来源和 SHA-256 哈希。

默认实例配置保存在 `src/scp_lab/data/devices/`。发布离线校验型号时，新增使用 `scp_lab.adapters.offline:create_backend` 的配置，并以 `package:relative/path.json` 格式设置 `options.model_resource`。本地接入也可以改用绝对路径 `options.model_file`。每个实例使用独立 JSON 配置，与用户设备目录共用加载器。

直接审阅型号定义，确保单位、范围和完成标准与描述的设备接口一致。

## 发布目录

```bash
uv build
uv run --no-sync python scripts/check_release.py dist
```

Wheel 包含独立型号文件和默认实例配置，源码包还包含双语指南、示例、测试和开发脚本。发布检查确认这些文件完整，并排除仅用于导入的原始资料和汇总型号数据。新增型号可按[离线接入教程](docs/zh-CN/backends.md#add-a-model-for-offline-validation)操作，SDK 适配器可参考[酶标仪软件包](examples/adapters)。

## 一并检查的内容

修改接口时，一并更新相关 schema、行为和文档。示例应在文档说明的安装环境中保持可运行。后端应说明参数校验、仿真、SDK 调用和物理观测分别检查或提供了什么，按行为变化运行相应检查。

设备专属输入、结果和可选观测属于该设备的 schema。修改共同消息结构时，应说明已有客户端与后端如何理解这些变化。

指南同时提供英文与简体中文版本，页面顶部有对应链接。修改面向使用方的行为或说明时，同步更新两种语言的相关内容，保持命令、字段和预期结果一致。
