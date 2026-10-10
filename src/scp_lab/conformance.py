"""Minimal, non-executing descriptor/state checks for locally registered backends."""

from .execution_models import DeviceDescriptor, DeviceState
from .schema_metadata import check_schema


def check_runtime(runtime) -> dict:
    devices = []
    for device_id in runtime.backends:
        try:
            descriptor = DeviceDescriptor.model_validate(runtime.describe_device(device_id))
            state = DeviceState.model_validate(runtime.device_state(device_id))
            if descriptor.device_id != state.device_id:
                raise ValueError("Descriptor and state must identify the same device")
            warnings = []
            for capability in descriptor.capabilities:
                check_schema(capability.input_schema)
                check_schema(capability.result_schema)
                warnings.extend(
                    {"capability_id": capability.capability_id, "message": message}
                    for message in capability.limitations
                )
            if descriptor.state_schema is not None:
                check_schema(descriptor.state_schema)
            devices.append(
                {
                    "device_id": device_id,
                    "status": "passed",
                    "capabilities_checked": len(descriptor.capabilities),
                    "warnings": warnings,
                }
            )
        except ValueError as error:
            devices.append({"device_id": device_id, "status": "failed", "error": str(error)})
    return {
        "status": "passed" if all(d["status"] == "passed" for d in devices) else "failed",
        "scope": "descriptor_and_state_schemas",
        "execution_performed": False,
        "limitations": [
            "Does not submit commands, test SDK execution or certify physical operation.",
            "Does not infer missing units, verify conversions or validate physical bounds.",
            "Backend read_state hooks must only return availability and cached observations.",
        ],
        "devices": devices,
    }
