"""MCP response envelopes; device and execution models remain transport-independent."""

from typing import Generic, Literal, TypeVar

from pydantic import ConfigDict, RootModel

from .execution_models import Contract, ExecutionError

Data = TypeVar("Data")


class DeviceSuccess(Contract, Generic[Data]):
    ok: Literal[True]
    data: Data


class DeviceFailure(Contract):
    ok: Literal[False]
    error: ExecutionError


class DeviceResponse(RootModel[DeviceSuccess[Data] | DeviceFailure], Generic[Data]):
    # Both union branches are objects, as required for an MCP output schema.
    model_config = ConfigDict(json_schema_extra={"type": "object"})
