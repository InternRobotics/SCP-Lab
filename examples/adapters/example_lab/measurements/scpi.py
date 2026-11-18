"""Measure a configured terminal using the instrument's documented SCPI query."""

import math
import socket
from functools import partial
from typing import Literal

from pydantic import Field

from scp_lab.device_config import DeviceConfig
from scp_lab.execution_models import Contract

from .backend import MeasurementBackend


class TCPConnection(Contract):
    host: str = Field(min_length=1)
    port: int = Field(ge=1, le=65535)


class BB3Connection(TCPConnection):
    port: int = Field(default=5025, ge=1, le=65535)
    channel: Literal["CH1", "CH2", "CH3", "CH4", "CH5", "CH6"]


class STEMlabConnection(TCPConnection):
    port: int = Field(default=5000, ge=1, le=65535)
    channel: Literal["AIN0", "AIN1", "AIN2", "AIN3"]


def read_voltage(connection: TCPConnection, command: str, channel: str) -> dict:
    with socket.create_connection((connection.host, connection.port), timeout=5) as sock:
        sock.sendall(f"{command} {channel}\r\n".encode("ascii"))
        with sock.makefile("rb") as stream:
            reply = stream.readline(128)
    if not reply.endswith(b"\n"):
        raise ValueError("Incomplete SCPI response")
    value = float(reply)
    if not math.isfinite(value):
        raise ValueError("Instrument returned a nonfinite voltage")
    return {"channel": channel, "voltage_v": value}


def create_bb3(config: DeviceConfig) -> MeasurementBackend:
    Contract.model_validate(config.options)
    connection = BB3Connection.model_validate(config.connection)
    return MeasurementBackend(
        config, "eez_bb3", partial(read_voltage, connection, "MEAS:VOLT?", connection.channel)
    )


def create_stemlab(config: DeviceConfig) -> MeasurementBackend:
    Contract.model_validate(config.options)
    connection = STEMlabConnection.model_validate(config.connection)
    return MeasurementBackend(
        config,
        "stemlab_125_14",
        partial(read_voltage, connection, "ANALOG:PIN?", connection.channel),
    )
