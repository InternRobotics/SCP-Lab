# 第一次设备调用

[English](../getting-started.md) · [文档目录](README.md) · [首页](../../README.zh-CN.md) · [安装](installation.md) · [应用与 Agent 接入](clients.md) · [设备接入](backends.md)

本页是一篇可选的入门教程，通过软件演示设备完成一次完整调用。先完成[安装](installation.md)，然后在仓库根目录运行以下命令。示例无需设备 SDK 或实验设备。

## 1. 完成第一次调用

```bash
uv run --no-sync python examples/quickstart.py
```

脚本会自动启动 MCP 服务，并保持连接直到请求完成。无需另外打开终端启动服务，也无需平台注册或模型 API key。

调用过程如下：

1. `list_devices` 发现演示加热器。
2. `describe_device` 获取其 `demo_heater.hold` 能力和输入 schema。
3. `submit_execution` 接受请求，返回包含 `run_id` 的执行记录。
4. `get_execution` 每次查询都返回当前执行记录。示例每隔 0.2 秒查询一次，在状态变化时打印，直到执行结束。
5. `get_device_state` 确认设备重新处于空闲状态。

[quickstart.py](../../examples/quickstart.py) 中的请求包含：

```json
{
  "device_id": "demo-heater",
  "capability_id": "demo_heater.hold",
  "arguments": {"target_celsius": 37, "duration_s": 1}
}
```

脚本还会附上刚刚发现的能力描述版本。若已发布接口发生变化，服务端可以据此拒绝不再匹配的请求。

## 2. 理解执行结果

终端会显示各步骤及观察到的状态变化。典型输出开头如下，其中 `<run_id>` 代表实际任务 ID：

```text
list_devices -> demo-heater (mock)
describe_device -> demo_heater.hold
submit_execution -> accepted (run_id=<run_id>)
Polling get_execution every 0.2 s; showing status changes.
get_execution -> running
get_execution -> succeeded
Result:
```

轮询是在读取同一个任务，不会重复提交实验。每次查询都返回当前状态和已上报的进度；示例只在状态变化时打印一行，完成后再打印最终结果：

```json
{
  "status": "succeeded",
  "execution_mode": "mock",
  "physical_execution": false,
  "evidence": "mock_trace",
  "result": {
    "requested_target_celsius": 37,
    "elapsed_demo_seconds": 1,
    "measured_temperature": null
  }
}
```

这里的 `evidence` 是示例为便于展示，对完整执行记录中 `completion_evidence.kind` 的简写。演示使用计时器：成功表示软件任务完成，`measured_temperature` 始终为 `null`。它不模拟热传递，也不返回实测温度。最后一行输出为 `get_device_state -> idle`。

## 3. 修改一个参数

打开 [quickstart.py](../../examples/quickstart.py)，修改 `request.arguments`，例如更换目标温度，或把持续时间改为两秒，再次运行同一命令。

查看该设备发布的 schema：

```bash
uv run --no-sync scp-lab device demo-heater
```

这个演示设备接受 4～95 摄氏度的目标值，持续时间须大于 0 且不超过 10 秒。schema 通过 `x-scp-unit` 声明单位。`target_celsius` 必填；省略 `duration_s` 时，后端使用声明的一秒默认值。完整执行记录同时保留提交参数和实际传给后端的生效参数。

## 选择下一步

| 目标 | 指南 |
| --- | --- |
| 继续体验代码生成与官方仿真 | [进阶教程：OT-2 仿真](ot2-examples.md) |
| 从自己的程序或 Agent 调用设备能力 | [应用与 Agent 接入](clients.md) |
| 接入仪器 SDK 或实验室服务 | [设备接入](backends.md) |
| 了解设备接口、执行模式和示例 | [设备目录](devices.md)与[示例目录](../../examples/README.zh-CN.md) |
| 查询消息字段与生命周期规则 | [协议参考](device-access.md) |

## 常见问题

| 现象 | 处理方式 |
| --- | --- |
| 手动启动服务后没有输出 | stdio MCP 服务正在等待客户端。运行 `quickstart.py`，脚本会自动启动并连接服务。 |
| 找不到此前返回的任务 ID | 在同一个服务会话中提交和查询；执行记录属于对应服务进程。 |
| `ot2-sim` 不可用 | 按 [OT-2 安装步骤](installation.md#ot-2-simulation)安装可选仿真环境。快速开始示例不依赖该环境。 |
| 请求被拒绝 | 检查设备 `input_schema` 中的必填项、单位、类型和范围。 |
