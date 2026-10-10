# 设备型号与适配器

[English](README.md) · [首页](../../../README.zh-CN.md) · [设备接入](../../../docs/zh-CN/backends.md)

45 个离线设备型号分别保存在 `<family>/models/` 下的独立 JSON 文件中。文件包含原生 SCP-Lab 能力定义，直接随软件包安装。它们既是应用可以调用的接口，也是接入新设备时的参考样例。

| 部分 | 职责 |
| --- | --- |
| `<family>/models/<model_id>.json` | 型号身份、能力、输入与结果 schema、完成条件 |
| [schemas.py](schemas.py) | 从包资源或本地绝对路径读取并检查一份型号文件 |
| [offline.py](offline.py) | 共用的离线校验实现与工厂 |
| [liquid/ot2.py](liquid/ot2.py) 和 [ot2_schemas.py](liquid/ot2_schemas.py) | OT-2 编译、官方仿真与生成的能力 schema |
| [heater/](heater) | 独立型号文件、schema 加载器和计时演示后端 |
| [../data/devices/](../data/devices) | 每个实例独立选择后端与型号的配置 |

例如，[Synergy H1 型号文件](plate_reader/models/agilent_biotek_synergy_h1.json)声明能力，[默认实例配置](../data/devices/agilent_biotek_synergy_h1-validation.json)选择离线工厂并直接指向该型号资源。多个实例可以选择同一文件，无需汇总 JSON、全局型号索引或目录生成步骤。

向已有类别添加型号无需修改 Python。新类别可以作为包含 `__init__.py` 和型号文件的 Python 包加入。需要额外检查、仿真或 SDK 调用时，再添加专属行为模块。外部适配器也可以在独立安装的软件包中采用同样结构。

按[完整设备教程](../../../docs/zh-CN/backends.md)注册实例、添加本地型号或开发适配器。[酶标仪示例包](../../../examples/adapters)分别保存型号定义、行为和 schema 加载逻辑。参数名称、单位、默认值和完成条件的约定见[协议参考](../../../docs/zh-CN/device-access.md)。
