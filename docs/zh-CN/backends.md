# 配置设备与开发后端

[English](../backends.md) · [用户指南](README.md) · [首页](../../README.zh-CN.md) · [应用接入](clients.md)

本指南介绍如何把设备能力提供给智能体或应用调用。接入时需要说明设备支持什么操作、怎样执行，以及使用哪份本地配置：

| 部分 | 需要提供的内容 | 酶标仪示例 |
| --- | --- | --- |
| 能力定义 | 操作名称、输入字段、结果格式和完成条件 | 读吸光度所需的板 ID、波长及结果格式 |
| 执行后端 | 检查请求或调用 SDK、仿真器、控制服务的代码 | 检查读取参数，或把读取请求交给酶标仪 SDK |
| 实例配置 | 一台设备的 ID、所用后端及连接设置 | `reader-01` 使用哪个后端、连接哪台仪器 |

能力定义可以单独保存在 JSON 文件中，由后端加载并提供给 SCP-Lab 登记。调用方通过 `describe_device` 查询能力定义和后端声明的执行方式（`execution_mode`）。

完成[基础安装](installation.md)后，按已有条件选择：

| 起点 | 接下来做什么 |
| --- | --- |
| 参考已登记型号的接口与配置 | [查看内置接入样例](#bundled-models-as-integration-examples) |
| 使用已有设备接口 | [配置实例](#configure-devices-with-an-existing-backend) |
| 发布新接口，进行离线校验 | [添加型号定义](#add-a-model-for-offline-validation) |
| 接入仿真器、SDK 或实验室服务 | [开发适配器](#develop-an-adapter-for-a-new-sdk-or-api) |

<a id="configure-devices-with-an-existing-backend"></a>
## 配置使用已有后端的设备

本节以 Synergy H1 酶标仪为例，说明如何配置设备实例、查询能力并提交读取请求。示例后端以 `schema_validation` 模式运行，目前支持参数和样品绑定校验，返回校验结果。

### 1. 保存实例配置

本例在项目根目录（包含 `pyproject.toml` 的目录）创建 `lab-devices/`：

```bash
mkdir -p lab-devices
```

配置目录也可以放在其他位置，后续命令中的 `--devices-dir` 使用对应路径。

将以下内容保存为 `lab-devices/reader-01.json`：

```json
{
  "schema_version": "scp-lab.device-config.v0.1",
  "device_id": "reader-01",
  "display_name": "Reader 01 - offline interface validation",
  "backend": "scp_lab.adapters.offline:create_backend",
  "enabled": true,
  "connection": {},
  "options": {
    "model_resource": "scp_lab.adapters.plate_reader:models/agilent_biotek_synergy_h1.json"
  }
}
```

这份配置指定了三个关键项：

| 配置项 | 本例的含义 |
| --- | --- |
| `device_id` | 调用时使用的设备 ID，由接入方自定义为非空字符串；`reader-01` 仅为示例，同一服务加载的实例配置中不能重复 |
| `backend` | 使用内置离线后端检查请求格式 |
| `options.model_resource` | 加载 [Synergy H1 能力定义](../../src/scp_lab/adapters/plate_reader/models/agilent_biotek_synergy_h1.json) |

<a id="how-a-backend-factory-works"></a>
`backend` 的格式为 `Python模块:该模块中创建后端的函数`。

本例的 `scp_lab.adapters.offline:create_backend` 对应以下调用：

```python
from scp_lab.adapters.offline import create_backend

backend = create_backend(config)
```

服务启动时，将每份启用的实例配置解析为 `DeviceConfig`，传给对应的工厂函数。返回的后端实例负责处理该设备后续的请求。

<a id="model-definition-location"></a>
`models/` 目录按设备型号保存能力定义 JSON，描述所提供的操作、输入与结果 schema，以及完成条件。内置离线后端通过以下配置找到要读取的文件：

| 配置项 | 文件位置 | 适用场景 |
| --- | --- | --- |
| `options.model_resource` | 已安装 Python 包内的文件，格式为 `package:relative/path.json` | 使用内置定义，或随自己的 Python 包分发定义 |
| `options.model_file` | SCP-Lab 服务所在机器上的文件，填写绝对路径 | 直接使用自己编写的 JSON，无需先打包安装 |

本例使用 `model_resource`：冒号前的 `scp_lab.adapters.plate_reader` 是 Python 包名，冒号后的 `models/agilent_biotek_synergy_h1.json` 是该包内的文件路径。

内置离线后端每个实例读取一份能力定义，`model_resource` 与 `model_file` 选择一种即可；改用本地文件时，将 `options` 中的 `model_resource` 替换为 `model_file`。

同型号设备使用相同接口和执行方式时，可以复用能力定义和后端代码。另存一份实例配置，设置不同的 `device_id`（例如 `reader-02`）。服务启动时会分别根据两份配置创建后端对象。本例的离线后端不需要连接信息，`connection` 保持 `{}`；接入真机时，应在各自的配置中填写对应设备的连接信息。

### 2. 检查已配置设备

在仓库根目录运行：

```bash
# 列出所选目录中的设备。
uv run --no-sync scp-lab devices --devices-dir ./lab-devices
# 查看 reader-01 的能力和输入、结果 schema。
uv run --no-sync scp-lab device reader-01 --devices-dir ./lab-devices
# 检查描述和状态的格式。
uv run --no-sync scp-lab check --devices-dir ./lab-devices
```

本例的设备列表中应出现 `reader-01`，执行模式为 `schema_validation`。`device` 返回的 `capabilities` 包含 `agilent_biotek_synergy_h1.plate_reading`。

`check` 成功时的输出节选：

```json
{
  "status": "passed",
  "execution_performed": false
}
```

这表示设备描述和状态格式检查通过，尚未执行设备操作。

指定 `--devices-dir` 后，服务只加载该目录顶层的 `*.json`，替换默认设备集合。本例目录中只有 `reader-01`，因此只会列出这一台设备。如需保留内置示例，将对应配置从 [data/devices](../../src/scp_lab/data/devices) 复制到此目录。修改配置或型号定义后，重启服务使其生效。

### 3. 连接并调用

```bash
uv run --no-sync scp-lab mcp-config --devices-dir ./lab-devices --output mcp-config.json
```

生成的配置通过 `SCP_LAB_DEVICES_DIR` 指向所选设备目录。按照[应用接入指南](clients.md)合并客户端配置并重启服务后，即可通过 `list_devices` 查询 `reader-01`。

查询设备描述，获取读取功能的 `input_schema`：

```python
from examples.device_client import call

descriptor = await call(client, "describe_device", {"device_id": "reader-01"})
capability = next(
    item for item in descriptor["capabilities"]
    if item["capability_id"] == "agilent_biotek_synergy_h1.plate_reading"
)
input_schema = capability["input_schema"]
print(list(input_schema["properties"]["parameters"]["properties"]))
print(input_schema["properties"]["bindings"]["required"])
```

输出分别为操作参数字段和必填的样品绑定：

```text
['mode', 'wavelength', 'excitation_wavelength', 'emission_wavelength', 'focal_height']
['sample']
```

本次提交的请求是读取样品板在 600 nm 下的吸光度，因此选择 `mode="absorbance"`、`wavelength=600`，并通过 `bindings.sample.resource_id` 指定样品板：

```python
accepted = await call(client, "submit_execution", {
    "request": {
        "device_id": "reader-01",
        "capability_id": capability["capability_id"],
        "arguments": {
            "parameters": {"mode": "absorbance", "wavelength": 600},
            "bindings": {"sample": {"resource_id": "sample-plate"}}
        }
    }
})
```

使用返回的任务 ID 查询执行记录，直到任务结束：

```python
record = await call(client, "get_execution", {"run_id": accepted["run_id"]})
```

成功记录节选：

```json
{
  "status": "succeeded",
  "execution_mode": "schema_validation",
  "completion_evidence": {"kind": "schema_validation"},
  "result": {
    "validated_command": {
      "capability_id": "agilent_biotek_synergy_h1.plate_reading",
      "parameters": {"mode": "absorbance", "wavelength": 600},
      "bindings": {"sample": {"resource_id": "sample-plate"}}
    }
  }
}
```

这里的成功表示参数和样品绑定符合已发布的 schema；`validated_command` 保存通过检查的请求内容，`result.source` 记录所用型号文件及其哈希。该后端返回校验报告，不产生实际吸光度读数。

完整的连接、轮询和结果处理方法见[应用接入指南](clients.md#2-发现并调用能力)及其链接的示例源码。

<a id="add-a-model-for-offline-validation"></a>
## 添加离线型号

如果已有型号定义中没有需要的操作，可以先编写自己的能力 JSON，再使用相同的离线后端检查请求。开发时可使用 `model_file` 直接加载本地文件，在实例配置中填写它的绝对路径。完整定义、配置和调用示例见[型号定义指南](models.md)。

<a id="bundled-models-as-integration-examples"></a>
## 参考内置型号与配置

项目内置 45 个型号的接口定义，提供 89 项能力。每个型号都有一份离线实例配置，可用于参考如何划分操作、定义输入字段和资源绑定，以及关联型号与后端。以下三个型号也是[多设备调用示例](../../examples/02_multi_device.py)所使用的接口：

| 型号 | 能力定义 | 实例配置 |
| --- | --- | --- |
| Hamilton STAR 移液工作站 | [hamilton_star.json](../../src/scp_lab/adapters/liquid/models/hamilton_star.json) | [hamilton_star-validation.json](../../src/scp_lab/data/devices/hamilton_star-validation.json) |
| Cytomat 6002 培养箱 | [cytomat_6002.json](../../src/scp_lab/adapters/storage/models/cytomat_6002.json) | [cytomat_6002-validation.json](../../src/scp_lab/data/devices/cytomat_6002-validation.json) |
| Synergy H1 酶标仪 | [agilent_biotek_synergy_h1.json](../../src/scp_lab/adapters/plate_reader/models/agilent_biotek_synergy_h1.json) | [agilent_biotek_synergy_h1-validation.json](../../src/scp_lab/data/devices/agilent_biotek_synergy_h1-validation.json) |

这些实例以 `schema_validation` 模式检查请求，`result_schema` 和 `completion_criteria` 分别描述校验报告和校验通过的条件，不连接对应型号的 SDK 或真机。

接入实际设备时，可参考这些文件的结构，并根据所用 SDK 和设备配置核对操作、参数范围、单位及样品位置；再定义实际返回的结果字段和完成条件，按下一节实现执行后端。部分内置字段仍有单位约定不明确的限制，见[设备目录](devices.md#接口目录)。

默认服务已登记这些离线实例，可以直接通过 `list_devices` 和 `describe_device` 查询。完整的调用方法和智能体测试用途见[使用内置接口测试智能体](clients.md#bundled-device-interface-environment)。

<a id="develop-an-adapter-for-a-new-sdk-or-api"></a>
## 为新的 SDK 或 API 开发适配器

### 1. 查看完整适配器示例

[examples/04_custom_backend.py](../../examples/04_custom_backend.py) 使用同一个适配器加载两台酶标仪，并分别读取吸光度。在仓库根目录运行：

```bash
uv run --no-sync python examples/04_custom_backend.py
```

成功输出节选：

```json
[
  {
    "device_id": "reader-01",
    "status": "succeeded",
    "result": {"values": {"A1": 0.123}, "synthetic": true}
  },
  {
    "device_id": "reader-02",
    "status": "succeeded",
    "result": {"values": {"A1": 0.246}, "synthetic": true}
  }
]
```

两台设备的 ID 和读数来自各自的[实例配置](../../examples/devices)，共用同一份能力定义和后端代码。本例用 `DemonstrationReaderSDK` 模拟酶标仪 SDK，返回配置好的合成读数，执行模式为 `mock`。

完整的[适配器包](../../examples/adapters)结构如下：

```text
examples/adapters/
├── pyproject.toml
└── example_lab/
    ├── __init__.py
    └── plate_reader/
        ├── __init__.py
        ├── models/example_reader.json
        ├── schemas.py
        └── backend.py
```

| 文件 | 作用 |
| --- | --- |
| [models/example_reader.json](../../examples/adapters/example_lab/plate_reader/models/example_reader.json) | 定义 `example_reader.read_absorbance`，输入板 ID 和波长，返回孔位读数 |
| [schemas.py](../../examples/adapters/example_lab/plate_reader/schemas.py) | 从包中加载型号定义 |
| [backend.py](../../examples/adapters/example_lab/plate_reader/backend.py) | 创建 SDK 客户端、执行请求并返回结果和状态 |
| [pyproject.toml](../../examples/adapters/pyproject.toml) | 声明包名、依赖和需要安装的 Python 包 |

### 2. 将能力对应到 SDK 调用

本节查看模板中的演示调用，示例 SDK 只返回合成读数。示例能力的 `input_schema` 接受 `plate_id` 和 `wavelength_nm`。调用方按此格式提交：

```json
{"plate_id": "plate-001", "wavelength_nm": 600}
```

后端加载独立保存的型号定义，将能力提供给 SCP-Lab，用于能力查询和请求校验：

```python
model = get_model()
self.capabilities = model.capabilities
```

执行时，`request.arguments` 就是上面的参数对象。示例通过 `execute()` 调用 SDK、报告进度，并返回读数与完成依据：

```python
async def execute(self, request: ExecutionRequest, context: ExecutionContext) -> BackendResult:
    context.report_progress({"stage": "reading"})
    reading = await self.sdk.read_absorbance(**request.arguments)
    self.observation = StateObservation(
        values={"last_plate_id": request.arguments["plate_id"]},
        observed_at=datetime.now(timezone.utc).isoformat(),
        source="demonstration_reader_sdk",
        kind="simulated",
    )
    return BackendResult(
        result=reading, completion_evidence=CompletionEvidence(kind="mock_trace")
    )
```

`reading` 成为执行记录中的 `result`，字段应符合能力的 `result_schema`。`self.observation` 保存最近读取的板及观测时间，通过 `read_state()` 提供给状态查询：

```python
def read_state(self) -> BackendState:
    return BackendState(observation=self.observation)
```

客户端调用 `get_device_state` 后，可以从 `observation.values.last_plate_id` 读取最近的板 ID；观测同时保留时间、来源和 `simulated` 标记。

实例配置通过 `create_backend(config)` 创建后端。示例中的 `synthetic_absorbance` 来自配置的 `options`：

```python
def create_backend(config: DeviceConfig) -> DeviceBackend:
    Contract.model_validate(config.connection)
    options = ReaderOptions.model_validate(config.options)
    return MyReaderBackend(config, DemonstrationReaderSDK(options.synthetic_absorbance))
```

真实集成可以在这里校验设备地址、端口等连接设置，并创建相应的 SDK 客户端。完整类定义和导入见 [backend.py](../../examples/adapters/example_lab/plate_reader/backend.py)。

### 3. 安装并注册适配器

适配器需要安装到运行 SCP-Lab 服务的 Python 环境。实例配置中的 `backend` 指定 Python 模块和工厂函数的导入路径，服务通过该路径加载已安装的适配器。

**复制模板**

建议将设备后端作为独立 Python 包维护，便于与 SCP-Lab 分别更新和发布。下面以将适配器工程放在 SCP-Lab 仓库旁边为例；目录位置可以自选，包括仓库内，安装时使用对应路径即可。

将整个 `examples/adapters/` 目录复制到 SCP-Lab 仓库旁边，并将复制后的目录命名为 `my_lab_backend/`。本例的目录结构为：

```text
workspace/
├── scp-lab/                  # SCP-Lab 仓库
└── my_lab_backend/           # 复制得到的适配器工程
    ├── pyproject.toml
    └── example_lab/
```

本例保留内部的 `example_lab/` 目录，因此后面的 Python 导入路径仍以 `example_lab` 开头。后续修改都在复制后的 `my_lab_backend/` 中进行。

**安装到 SCP-Lab 环境**

在 SCP-Lab 仓库根目录运行。`../my_lab_backend` 指向上一步复制的目录：

```bash
uv pip install --python .venv/bin/python --no-deps -e ../my_lab_backend
```

Windows 将 `.venv/bin/python` 替换为 `.venv/Scripts/python.exe`。如果适配器工程放在其他位置，将 `../my_lab_backend` 替换为实际路径。

`-e` 表示开发安装，修改适配器代码后重启服务即可使用。`--no-deps` 表示不安装依赖；模板所需的 SCP-Lab 已在基础安装中安装，示例 SDK 也不需要额外依赖。

确认当前环境能够导入复制的包：

```bash
uv run --no-sync python -c "import example_lab; print(example_lab.__file__)"
```

输出路径应指向 `my_lab_backend/example_lab/__init__.py`。

**保存设备配置**

在 SCP-Lab 仓库根目录创建 `lab-devices/`（如果尚不存在），将以下内容保存为 `lab-devices/reader-01.json`。如果已保存前面的离线酶标仪配置，用此内容替换原文件，将 `reader-01` 切换到刚安装的后端：

```json
{
  "device_id": "reader-01",
  "backend": "example_lab.plate_reader.backend:create_backend",
  "connection": {},
  "options": {"synthetic_absorbance": 0.123}
}
```

`backend` 对应复制目录中 `example_lab/plate_reader/backend.py` 的 `create_backend` 函数，`options.synthetic_absorbance` 指定演示读数。

**检查并连接**

仍在 SCP-Lab 仓库根目录运行：

```bash
uv run --no-sync scp-lab check --devices-dir ./lab-devices
uv run --no-sync scp-lab mcp-config --devices-dir ./lab-devices --output mcp-config.json
```

`check` 应返回 `status="passed"`，表示配置和接口检查通过。按照[应用接入指南](clients.md)将生成的 MCP 配置合并到客户端配置中，并重启服务。

通过 `describe_device` 可读到 `example_reader.read_absorbance` 及其输入字段。提交请求的核心片段：

```python
accepted = await call(client, "submit_execution", {
    "request": {
        "device_id": "reader-01",
        "capability_id": "example_reader.read_absorbance",
        "arguments": {"plate_id": "plate-001", "wavelength_nm": 600}
    }
})
```

继续用 `accepted["run_id"]` 查询 `get_execution`。成功后，`result.values.A1` 为配置的 `0.123`，`result.synthetic` 为 `true`，完成依据为 `mock_trace`。新增一份具有不同 ID 和配置值的 JSON，即可登记第二个实例，如完整示例中的 `reader-02`。

### 4. 接入真实设备

接入真实设备时，需要通过设备控制软件、厂商 SDK 或其他控制接口执行实际操作。本节沿用上一节复制并安装的 `my_lab_backend/` 工程，先完善 schema 和参数校验，再将示例 SDK 调用替换为实际设备调用。

以下路径和类名沿用酶标仪示例，接入其他设备时使用对应的文件和后端类。`pyproject.toml` 和 `example_lab/` 下的文件都位于 `my_lab_backend/` 中；设备实例配置仍放在 SCP-Lab 仓库的 `lab-devices/` 中。

**先修改 schema 和参数校验**

| 本例修改哪个文件 | 具体修改 |
| --- | --- |
| `example_lab/plate_reader/models/example_reader.json` | 按实际设备调整操作名称、输入字段、单位和参数范围 |
| `example_lab/plate_reader/schemas.py` | 如果型号 JSON 改了名称或位置，更新 `get_model()` 中的加载路径；否则保持原样 |
| `example_lab/plate_reader/backend.py` | 需要补充 schema 以外的校验时，在后端类中实现 `validate(request)`，并保留 `super().validate(request)` 的检查；本例后端类为 `MyReaderBackend` |

这些检查不启动实验。接入实际接口前，可继续使用 `mock` 验证调用流程；若能力的输入或结果格式改变，也要同步调整演示实现。本例需调整同一 `backend.py` 中的 `DemonstrationReaderSDK` 及其调用代码。

**再修改后端，接入 SDK**

先在 `my_lab_backend/pyproject.toml` 中添加 SDK 依赖，再从 SCP-Lab 仓库根目录运行安装命令。这次去掉 `--no-deps`，以安装新增依赖：

```bash
uv pip install --python .venv/bin/python -e ../my_lab_backend
```

Windows 的解释器路径替换方式与上一节相同。然后修改 `my_lab_backend/example_lab/plate_reader/backend.py`，下面各项都在这个文件中：

| 本例修改哪里 | 具体修改 |
| --- | --- |
| `create_backend(config)` | 定义并校验 `connection` 和 `options` 中需要的设置，用它们创建真实 SDK 客户端，替换本例的 `DemonstrationReaderSDK` |
| `MyReaderBackend.__init__()` 中的 `description` | 设置 `execution_mode="hardware"` 和 `physical_execution=True` |
| `execute(request, context)` | 将请求参数对应到 SDK 调用，整理实际返回结果，并根据设备反馈返回完成依据 |
| `read_state()` 及观测更新代码 | 返回可用性和缓存观测，保留观测的时间、来源及种类 |

如果设备通过 HTTP 服务或串口控制，也在这个文件中实现相应调用。设备操作放在 `execute()` 中；创建后端、解析默认值、校验参数和读取状态均不得启动实验。阻塞式 SDK 调用可以放在线程中运行，将进度回传事件循环后再调用 `context.report_progress(...)`。

返回结果时，确认设备可以接收下一项操作后，返回 `device_released=True`；无法确认结果时返回 `unknown`，设备会保持 `needs_attention`。支持取消的后端也需要确认操作已停止。具体约定见[完成依据](device-access.md#completion-evidence)和[执行生命周期](device-access.md#执行生命周期与占用)。

**更新结果定义和设备配置**

根据 SDK 的实际返回值，更新 `my_lab_backend/example_lab/plate_reader/models/example_reader.json` 中的 `result_schema` 和 `completion_criteria`。本例的结果要求 `synthetic=true`，接入真机后应删除或调整这个要求，让结果格式和完成条件与实际反馈一致。

在 SCP-Lab 仓库的 `lab-devices/reader-01.json` 中，将设备地址、端口等填入后端支持的 `connection` 字段，删除演示用的 `options.synthetic_absorbance`，并填写实际需要的选项。本例继续使用 `reader-01`；如果 Python 模块和工厂函数路径未变，`backend` 保持原值。

建议将能力定义、后端代码和调用示例一起维护，修改参数、返回字段或完成条件时同步更新。

**重启并验证**

前面使用了 `-e` 开发安装，修改同一工程中的代码和型号 JSON 后，重启服务即可加载。服务启动命令和设备目录未变时，沿用已有 MCP 配置。重启后，从 SCP-Lab 仓库根目录运行：

```bash
uv run --no-sync scp-lab check --devices-dir ./lab-devices
```

`check` 检查描述和状态格式。随后沿用上一节的调用方法，通过 `describe_device` 确认 `execution_mode="hardware"`，按更新后的能力定义提交请求并查询结果。核对参数处理、结果和完成依据是否符合定义，并验证无效输入、失败及已支持的取消流程。

增加另一台使用相同能力定义和后端的设备时，只需新增实例配置并使用不同的 `device_id`，无需再次复制工程。接入需要不同控制代码的设备时，可以在 `my_lab_backend/example_lab/` 下新增对应目录，并在新实例配置中指定它的后端工厂函数。

<a id="validation-and-execution-stages"></a>
## 校验与执行阶段

`execution_mode` 表示实例当前采用的执行方式。各设备可以支持不同方式，不要求逐级接入。

| 执行方式 | 本次调用做什么 | 典型结果 | 成功的含义 |
| --- | --- | --- | --- |
| `schema_validation` | 按已发布的 schema 检查请求 | 校验报告 | 请求格式和声明的约束检查通过 |
| `mock` | 执行演示流程 | 合成读数或演示记录 | 演示流程完成 |
| `official_simulation` | 调用官方仿真器 | 仿真记录 | 仿真程序完成 |
| `hardware` | 通过设备控制接口操作真机 | 实际读数或操作反馈 | 实际反馈支持声明的完成条件 |

不同执行方式的输入格式、结果格式和完成条件可以不同，分别由所选实例的 `input_schema`、`result_schema` 和 `completion_criteria` 说明。`completion_evidence` 记录本次调用提供的完成依据。

提交请求时，运行时先检查输入 schema、按声明的策略[处理默认值](device-access.md#units-and-defaults)，再调用后端的 `validate()`；请求接受后才调用 `execute()`。成功结果还会按 `result_schema` 检查，随后供 `get_execution` 查询。

调用前通过 `describe_device` 读取所选实例的描述。例如，`ot2-validation` 与 `ot2-sim` 的输入 schema 不同，需要按各自的格式构造请求。

## 设备实例配置参考

| 字段 | 含义 |
| --- | --- |
| `schema_version` | 默认为 `scp-lab.device-config.v0.1` |
| `device_id` | 必填，唯一实例 ID，重启后保持稳定 |
| `backend` | 必填，指定创建后端的模块与函数，见[格式说明](#how-a-backend-factory-works)。返回的后端提供设备描述 `description`、能力列表 `capabilities`，以及请求校验 `validate()`、执行 `execute()` 和状态查询 `read_state()` 方法 |
| `display_name` | 可选，覆盖适配器默认显示名称 |
| `enabled` | 布尔值，默认为 `true`；禁用实例不会被创建 |
| `connection` | 适配器专属连接设置，默认为 `{}` |
| `options` | 适配器专属配置，默认为 `{}` |

[配置 schema](../../schemas/device-config.schema.json)定义实例文件的字段，各适配器检查自己的连接设置和选项。设备地址和凭据应保留在本地配置或适配器管理的凭据来源中。除非另有说明，文件设置使用绝对路径。

目录选择顺序为 `--devices-dir`、`SCP_LAB_DEVICES_DIR`、内置默认目录。文件按名称顺序读取；重复 ID（包括禁用条目）和格式错误会被拒绝，空目录不发布实例。

| 内置后端工厂 | 选项 | 模式 |
| --- | --- | --- |
| `scp_lab.adapters.offline:create_backend` | 用 `model_resource` 或 `model_file` 指定[能力定义的位置](#model-definition-location) | `schema_validation` |
| `scp_lab.adapters.liquid.ot2:create_backend` | 空，通过 `SCP_LAB_SIM_PYTHON` 选择仿真器 | `official_simulation` |
| `scp_lab.adapters.heater.backend:create_backend` | 可选布尔值 `fail` | `mock` |

## 配置更新与常见问题

型号定义和实例配置保存在文件中，修改后重启服务生效。当前版本的通用任务记录只保存在正在运行的服务中，重启后旧的 `run_id` 无法继续查询；多个独立服务也不会互相知道设备是否忙碌。相关处理见[应用接入指南](clients.md#4-处理执行结果)。OT-2 仿真记录另行保存为 JSON 文件。

| 现象 | 处理方式 |
| --- | --- |
| 无法导入适配器 | 将其安装到 MCP 配置指定的解释器中；移动环境后重新生成配置。 |
| 无法加载型号 | 检查错误中的文件名、包资源或本地绝对路径；型号文件应放在实例目录之外。 |
| 默认示例消失 | 显式设备目录会替换默认集合，将所需内置配置复制到其中。 |
| 设备 ID 重复 | 每份实例文件都使用唯一 ID，包括禁用条目。 |
| 任务后处于 `needs_attention` | 查看执行记录和设备实际状态，确认操作执行到哪一步。当前版本没有手工清除占用的接口；重启服务不能证明设备已停止。 |
