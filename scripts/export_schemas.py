"""Regenerate public schemas from the validation models."""

import json
from pathlib import Path

from scp_lab.adapters.schemas import DeviceModel
from scp_lab.capabilities import list_capabilities, protocol_schema
from scp_lab.device_config import DeviceConfig
from scp_lab.execution_models import (
    DeviceDescriptor,
    DeviceState,
    ExecutionRecord,
    ExecutionRequest,
)

directory = Path(__file__).resolve().parents[1] / "schemas"
directory.mkdir(exist_ok=True)
for filename, value in (
    ("protocol.schema.json", protocol_schema()),
    ("ot2-capabilities.json", list_capabilities()),
    ("execution-request.schema.json", ExecutionRequest.model_json_schema()),
    ("execution-record.schema.json", ExecutionRecord.model_json_schema()),
    ("device-descriptor.schema.json", DeviceDescriptor.model_json_schema()),
    ("device-state.schema.json", DeviceState.model_json_schema()),
    ("device-config.schema.json", DeviceConfig.model_json_schema()),
    ("device-model.schema.json", DeviceModel.model_json_schema()),
):
    (directory / filename).write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
