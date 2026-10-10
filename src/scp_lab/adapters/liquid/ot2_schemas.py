"""OT-2 capability schemas generated from its compiler models."""

from copy import deepcopy

from scp_lab.capabilities import list_capabilities
from scp_lab.execution_models import Capability, Contract
from scp_lab.models import InitialLiquid, Setup


class OT2Arguments(Contract):
    setup: Setup
    liquids: list[InitialLiquid]
    parameters: dict


def get_capabilities() -> list[Capability]:
    capabilities = []
    for item in list_capabilities():
        schema = OT2Arguments.model_json_schema()
        parameters = deepcopy(item["input_schema"])
        schema.setdefault("$defs", {}).update(parameters.pop("$defs", {}))
        schema["properties"]["parameters"] = parameters
        capabilities.append(
            Capability(
                capability_id=item["capability_id"],
                description=item["description"],
                input_schema=schema,
                result_schema={
                    "type": "object",
                    "required": ["run_id", "status", "physical_execution"],
                },
                completion_criteria="Opentrons 8.8.2 official simulator completes without error; physical effects are not measured.",
                access_level=item["access_level"],
                defaults_policy="backend_resolved",
            )
        )
    return capabilities
