import pytest

from scp_lab.adapters.schemas import load_model
from scp_lab.device_config import load_device_configs


@pytest.fixture
def device_models():
    return [
        load_model(**config.options)
        for _, config in load_device_configs()
        if config.backend == "scp_lab.adapters.offline:create_backend"
    ]
