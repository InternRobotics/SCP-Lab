"""Versioned, strict experiment requests with explicit physical units."""

from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field

Identifier = Annotated[str, Field(pattern=r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")]
Positive = Annotated[float, Field(gt=0, allow_inf_nan=False)]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True)


class WellRef(Model):
    labware: Identifier
    well: Annotated[str, Field(pattern=r"^[A-H](?:[1-9]|1[0-2])$")]


class Labware(Model):
    id: Identifier
    load_name: str
    location: str = Field(description="OT-2 slot 1–11 or a declared module ID")


class Module(Model):
    id: Identifier
    kind: Literal["temperature", "heater_shaker", "thermocycler", "magnetic"]
    slot: Annotated[int, Field(ge=1, le=11)]


class Pipette(Model):
    model: Literal["p20_single_gen2", "p300_single_gen2", "p1000_single_gen2"]
    mount: Literal["left", "right"] = "left"
    tip_racks: Annotated[list[Identifier], Field(min_length=1)]


class Setup(Model):
    labware: Annotated[list[Labware], Field(min_length=1, max_length=11)]
    modules: Annotated[list[Module], Field(max_length=4)] = Field(default_factory=list)
    pipette: Pipette | None = None


class InitialLiquid(Model):
    sample_id: Identifier
    location: WellRef
    volume_ul: Positive = Field(json_schema_extra={"x-scp-unit": "uL"})


class Step(Model):
    id: Identifier


class Transfer(Step):
    action: Literal["liquid_transfer"] = "liquid_transfer"
    source: WellRef
    destination: WellRef
    volume_ul: Positive = Field(json_schema_extra={"x-scp-unit": "uL"})


class Distribute(Step):
    action: Literal["liquid_distribution"] = "liquid_distribution"
    source: WellRef
    destinations: Annotated[list[WellRef], Field(min_length=1, max_length=96)]
    volume_per_destination_ul: Positive = Field(json_schema_extra={"x-scp-unit": "uL"})


class Consolidate(Step):
    action: Literal["liquid_consolidation"] = "liquid_consolidation"
    sources: Annotated[list[WellRef], Field(min_length=1, max_length=96)]
    destination: WellRef
    volume_per_source_ul: Positive = Field(json_schema_extra={"x-scp-unit": "uL"})


class Mix(Step):
    action: Literal["pipette_mixing"] = "pipette_mixing"
    sample: WellRef
    volume_ul: Positive = Field(json_schema_extra={"x-scp-unit": "uL"})
    repetitions: Annotated[int, Field(ge=1, le=100)]


class Incubate(Step):
    action: Literal["incubation"] = "incubation"
    labware: Identifier
    temperature_c: Annotated[float, Field(ge=4, le=95)] = Field(
        json_schema_extra={"x-scp-unit": "degC"}
    )
    duration_s: Positive = Field(json_schema_extra={"x-scp-unit": "s"})


class Shake(Step):
    action: Literal["orbital_shaking"] = "orbital_shaking"
    labware: Identifier
    speed_rpm: Annotated[int, Field(ge=200, le=3000)] = Field(
        json_schema_extra={"x-scp-unit": "rpm"}
    )
    duration_s: Positive = Field(json_schema_extra={"x-scp-unit": "s"})


class ThermalStage(Model):
    temperature_c: Annotated[float, Field(ge=4, le=99)] = Field(
        json_schema_extra={"x-scp-unit": "degC"}
    )
    duration_s: Positive = Field(json_schema_extra={"x-scp-unit": "s"})


class ThermalCycle(Step):
    action: Literal["thermal_cycling"] = "thermal_cycling"
    labware: Identifier
    cycles: Annotated[int, Field(ge=1, le=100)]
    lid_temperature_c: Annotated[float, Field(ge=37, le=110)] = Field(
        default=105, json_schema_extra={"x-scp-unit": "degC"}
    )
    block_max_volume_ul: Annotated[float, Field(gt=0, le=100)] = Field(
        json_schema_extra={"x-scp-unit": "uL"}
    )
    profile: Annotated[list[ThermalStage], Field(min_length=1, max_length=20)]


class MagneticHold(Step):
    action: Literal["magnetic_separation"] = "magnetic_separation"
    labware: Identifier
    height_from_base_mm: Annotated[float, Field(ge=0, le=20)] = Field(
        json_schema_extra={"x-scp-unit": "mm"}
    )
    duration_s: Positive = Field(json_schema_extra={"x-scp-unit": "s"})


class Delay(Step):
    action: Literal["delay"] = "delay"
    duration_s: Positive = Field(json_schema_extra={"x-scp-unit": "s"})


Action = Annotated[
    Union[
        Transfer, Distribute, Consolidate, Mix, Incubate, Shake, ThermalCycle, MagneticHold, Delay
    ],
    Field(discriminator="action"),
]
ACTION_MODELS = (
    Transfer,
    Distribute,
    Consolidate,
    Mix,
    Incubate,
    Shake,
    ThermalCycle,
    MagneticHold,
    Delay,
)


class Protocol(Model):
    schema_version: Literal["scp-lab.protocol.v0.1"] = "scp-lab.protocol.v0.1"
    name: Annotated[str, Field(min_length=1, max_length=200)]
    experiment_id: Identifier
    device_id: Literal["ot2"] = "ot2"
    api_level: Literal["2.20"] = "2.20"
    setup: Setup
    liquids: Annotated[list[InitialLiquid], Field(max_length=1056)] = Field(default_factory=list)
    steps: Annotated[list[Action], Field(min_length=1, max_length=500)]
