# SCP-Lab user guide

[简体中文](zh-CN/README.md) · [Home](../README.md)

Complete installation, then choose a tutorial or an integration guide to suit your task.

## Installation

The [installation guide](installation.md) covers source acquisition, dependencies, and environment verification.

## Tutorials

| Guide | What you will learn |
| --- | --- |
| [Introduction: your first device call](getting-started.md) | Run the mock heater and understand discovery, submission, and execution feedback |
| [Advanced: OT-2 simulation](ot2-examples.md) | Generate pipetting code, run it in the official simulator, and inspect the resulting evidence |

## Integration guides

| Guide | What you will learn |
| --- | --- |
| [Application integration](clients.md) | Configure an MCP client, call capabilities, and handle execution outcomes |
| [Device integration](backends.md) | Register instances and develop a reusable SDK adapter |
| [Offline model definitions](models.md) | Add capability schemas and validate calls through the shared backend |

## Design and reference

| Reference | Contents |
| --- | --- |
| [Design guide](design.md) | Access levels, capability/state/execution objects, completion evidence, and MCP compatibility |
| [Device catalog](devices.md) | Available instances, model interfaces, and execution modes |
| [Protocol reference](device-access.md) | Messages, units, defaults, state, lifecycle, and evidence |
| [JSON Schemas](../schemas/README.md) | Public message and configuration schemas |
| [Examples](../examples/README.md) | Runnable clients and expected feedback |
| [Model definitions](../src/scp_lab/adapters) | Capability definitions grouped by device class |
| [Contributing](../CONTRIBUTING.md) | Development setup, checks, and generated files |

Each guide has an English and a Simplified Chinese version, linked at the top. Commands, API names, and data formats are the same in both versions.
