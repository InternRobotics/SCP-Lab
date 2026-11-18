"""Read Tinkerforge Bricklets by their hardware UID using the manufacturer's bindings."""

from functools import partial
from typing import Literal

from pydantic import Field
from tinkerforge.bricklet_co2_v2 import BrickletCO2V2
from tinkerforge.bricklet_color_v2 import BrickletColorV2
from tinkerforge.bricklet_humidity_v2 import BrickletHumidityV2
from tinkerforge.bricklet_load_cell_v2 import BrickletLoadCellV2
from tinkerforge.ip_connection import IPConnection

from scp_lab.device_config import DeviceConfig
from scp_lab.execution_models import Contract

from .backend import MeasurementBackend


class BrickConnection(Contract):
    host: str = Field(min_length=1)
    port: int = Field(default=4223, ge=1, le=65535)
    uid: str = Field(min_length=1, max_length=8, pattern=r"^[1-9a-km-zA-HJ-NP-Z]+$")


class BrickOptions(Contract):
    model: Literal["load_cell_v2", "co2_v2", "color_v2", "humidity_v2"]


def read_color(device: BrickletColorV2) -> dict:
    color = device.get_color()
    return {"red": color.r, "green": color.g, "blue": color.b, "clear": color.c}


READERS = {
    "load_cell_v2": (BrickletLoadCellV2, lambda d: {"weight_g": d.get_weight()}),
    "co2_v2": (BrickletCO2V2, lambda d: {"co2_ppm": d.get_co2_concentration()}),
    "color_v2": (BrickletColorV2, read_color),
    "humidity_v2": (
        BrickletHumidityV2,
        lambda d: {"relative_humidity_percent": d.get_humidity() / 100},
    ),
}


def read_bricklet(connection: BrickConnection, model: str) -> dict:
    device_type, read = READERS[model]
    ipcon = IPConnection()
    ipcon.set_auto_reconnect(False)
    device = device_type(connection.uid, ipcon)
    ipcon.connect(connection.host, connection.port)
    try:
        return read(device)
    finally:
        ipcon.disconnect()


def create_backend(config: DeviceConfig) -> MeasurementBackend:
    connection = BrickConnection.model_validate(config.connection)
    model = BrickOptions.model_validate(config.options).model
    return MeasurementBackend(config, model, partial(read_bricklet, connection, model))
