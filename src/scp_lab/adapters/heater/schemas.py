"""Load the heater's capability definitions independently of its behavior."""

from scp_lab.adapters.schemas import load_model


def get_capabilities():
    return load_model(
        model_resource=f"{__package__}:models/demo_heater.json"
    ).definition.capabilities
