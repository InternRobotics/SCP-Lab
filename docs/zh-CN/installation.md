# 安装 SCP-Lab

[English](../installation.md) · [用户指南](README.md) · [首页](../../README.zh-CN.md)

本页介绍从源码安装 SCP-Lab 并准备本地环境。安装完成后，可以按需体验设备调用与仿真教程，或直接接入智能体和设备。

## 环境准备

- Git：通过克隆获取仓库时使用，也可以下载并解压完整仓库压缩包。
- [uv](https://docs.astral.sh/uv/getting-started/installation/)：管理 Python、虚拟环境和依赖。
- 首次下载依赖时需要联网。以下命令使用 Python 3.12；本机没有该版本时，uv 可以自动下载。

以下命令适用于 macOS/Linux 终端和 Windows PowerShell。安装 Git 和 uv 后，重新打开终端并检查：

```bash
git --version
uv --version
```

## 1. 获取源码

克隆仓库并进入本地 `scp-lab` 目录。

```bash
git clone https://github.com/InternRobotics/SCP-Lab.git scp-lab
cd scp-lab
```

如果已经下载或克隆了仓库，直接在仓库根目录打开终端即可。根目录包含 `pyproject.toml`、`uv.lock` 和 `src/`，后续命令均在此处运行。

## 2. 安装依赖

```bash
uv sync --frozen --python 3.12 --extra mcp
```

命令会创建 `.venv`，安装 SCP-Lab 及其 MCP 接口和客户端所需的依赖。`--frozen` 使用仓库已有的依赖锁文件。每台电脑分别创建环境，不要在机器之间复制 `.venv`。

指南使用 `uv run --no-sync` 在该环境中执行命令，不重复同步依赖，无需手动激活 `.venv`。

## 3. 验证安装

```bash
uv run --no-sync scp-lab --help
```

输出应包含 `serve`、`devices`、`device`、`mcp-config` 等命令。此步骤检查命令行入口能否加载，不会发起实验。

## 可选依赖

<a id="ot-2-simulation"></a>
### OT-2 仿真

运行 [OT-2 进阶教程](ot2-examples.md)或使用 `ot2-sim` 后端时，需要安装此环境。Opentrons 依赖单独安装在 `.venv-sim` 中，与 SCP-Lab 主环境分开。以下命令均在仓库根目录执行。

macOS/Linux：

```bash
uv venv --python 3.12 .venv-sim
uv pip sync --python .venv-sim/bin/python requirements-simulation.lock
.venv-sim/bin/opentrons_simulate --version
```

Windows PowerShell：

```powershell
uv venv --python 3.12 .venv-sim
uv pip sync --python .venv-sim/Scripts/python.exe requirements-simulation.lock
.venv-sim/Scripts/opentrons_simulate.exe --version
```

最后一条命令用于检查已安装的仿真器版本。使用当前锁文件安装后，预期输出为：

```text
opentrons_simulate 8.8.2
```

配置并运行仿真见[进阶教程](ot2-examples.md)。接入 MCP 客户端时，在安装后生成[客户端配置](clients.md)，将仿真环境一并写入配置。

## 选择下一步

| 目标 | 指南 |
| --- | --- |
| 通过演示调用了解交互过程 | [第一次设备调用](getting-started.md)，可选的入门教程 |
| 体验代码生成与官方仿真 | [进阶教程：OT-2 仿真](ot2-examples.md) |
| 接入智能体或应用 | [应用接入](clients.md) |
| 配置自己的设备或开发执行后端 | [设备接入与后端开发](backends.md) |
| 修改 SCP-Lab 代码并运行测试 | [贡献指南](../../CONTRIBUTING.zh-CN.md) |

## 常见问题

| 现象 | 处理方式 |
| --- | --- |
| 找不到 `git` 或 `uv` | 安装对应工具后重新打开终端，确保其可执行文件位于 `PATH`。仅克隆仓库需要 Git。 |
| 找不到 `pyproject.toml` | 在仓库根目录运行命令，不要在其父目录或 `src/` 中运行。 |
| 无法导入 `mcp` | 安装命令包含 `--extra mcp`，后续在仓库根目录使用 `uv run --no-sync`。 |
