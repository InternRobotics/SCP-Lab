"""Load one model definition from an installed package or an explicit local file."""

import json
import re
from dataclasses import dataclass
from hashlib import sha256
from importlib.resources import files
from pathlib import Path, PurePosixPath
from typing import Literal

from jsonschema import Draft202012Validator, SchemaError
from pydantic import Field, model_validator

from scp_lab.execution_models import Capability, Contract


class DeviceModel(Contract):
    """Adapter-owned capability definitions; instance and connection settings live elsewhere."""

    schema_version: Literal["scp-lab.device-model.v0.1"] = "scp-lab.device-model.v0.1"
    model_id: str = Field(min_length=1)
    device_class: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    capabilities: list[Capability] = Field(min_length=1)
    state_schema: dict | None = None

    @model_validator(mode="after")
    def valid_capabilities(self):
        json.dumps(self.model_dump(), allow_nan=False)
        ids = [c.capability_id for c in self.capabilities]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate capability_id in model definition")
        for capability in self.capabilities:
            Draft202012Validator.check_schema(capability.input_schema)
            Draft202012Validator.check_schema(capability.result_schema)
        if self.state_schema is not None:
            Draft202012Validator.check_schema(self.state_schema)
        return self


@dataclass
class LoadedModel:
    definition: DeviceModel
    source: dict[str, str]


def _unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def load_model(
    *, model_resource: str | None = None, model_file: str | Path | None = None
) -> LoadedModel:
    """Read exactly one file. No model registry, generated catalog, or global cache is needed."""
    if (model_resource is None) == (model_file is None):
        raise ValueError("Specify exactly one of model_resource or model_file")
    location = model_resource if model_resource is not None else str(model_file)
    try:
        if model_resource is not None:
            package, separator, relative = model_resource.partition(":")
            path = PurePosixPath(relative)
            if (
                not separator
                or not re.fullmatch(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*", package)
                or not relative
                or path.is_absolute()
                or ".." in path.parts
                or "\\" in relative
                or path.suffix != ".json"
            ):
                raise ValueError("model_resource must be package:relative/path.json")
            content = files(package).joinpath(*path.parts).read_bytes()
            source = {"model_resource": model_resource}
        else:
            path = Path(model_file).expanduser()
            if not path.is_absolute():
                raise ValueError("model_file must be an absolute path")
            content = path.read_bytes()
            source = {"model_file": str(path)}
        definition = DeviceModel.model_validate(
            json.loads(content.decode("utf-8"), object_pairs_hook=_unique_keys)
        )
    except (ValueError, OSError, ImportError, TypeError, SchemaError) as error:
        raise ValueError(f"Cannot load model {location!r}: {error}") from error
    return LoadedModel(definition, {**source, "sha256": sha256(content).hexdigest()})
