"""Load the reader definition shipped with this adapter package."""

from scp_lab.adapters.schemas import load_model


def get_model():
    return load_model(model_resource=f"{__package__}:models/example_reader.json").definition
