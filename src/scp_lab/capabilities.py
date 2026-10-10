"""Capability descriptions are generated from the same models used for validation."""

from .labware import DEFINITIONS
from .models import ACTION_MODELS, Protocol

DESCRIPTIONS = {
    "liquid_transfer": "Transfer liquid between two wells using one fresh tip.",
    "liquid_distribution": "Transfer to each destination with a fresh tip per destination; no bulk aspiration.",
    "liquid_consolidation": "Transfer from each source with a fresh tip per source; no pooled aspiration.",
    "pipette_mixing": "Mix declared liquid in a well using a fresh tip.",
    "incubation": "Set a Temperature Module, wait at target for the duration, then deactivate.",
    "orbital_shaking": "Latch, shake on a Heater-Shaker, then stop shaking.",
    "thermal_cycling": "Close lid, execute the thermal profile, deactivate and reopen lid.",
    "magnetic_separation": "Engage a Magnetic Module at explicit height, hold, then disengage.",
    "delay": "Wait for a declared interval within the protocol.",
}


def list_capabilities() -> list[dict]:
    result = []
    for model in ACTION_MODELS:
        schema = model.model_json_schema()
        action = model.model_fields["action"].default
        schema["properties"].pop("id")
        schema["properties"].pop("action")
        schema["required"] = [k for k in schema.get("required", []) if k not in ("id", "action")]
        result.append(
            {
                "capability_id": f"ot2.{action}",
                "version": "0.1.0",
                "device_id": "ot2",
                "access_level": "L3" if action != "delay" else None,
                "description": DESCRIPTIONS[action],
                "input_schema": schema,
                "execution_modes": ["compile", "official_simulation"],
                "implementation_status": "implemented",
                "hardware_validation": "not_performed",
                "simulation_validation": "reported_per_run",
                "completion_criteria": "Official simulator returns without error; this establishes simulation completion only.",
                "setup_required": True,
            }
        )
    return result


def protocol_schema() -> dict:
    return Protocol.model_json_schema()


def supported_labware() -> dict:
    from dataclasses import asdict

    return {name: asdict(definition) for name, definition in DEFINITIONS.items()}
