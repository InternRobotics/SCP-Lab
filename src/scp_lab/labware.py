"""Small reviewed labware subset. Capacities are planning limits, not measurements."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Definition:
    rows: str
    columns: int
    capacity_ul: float
    tip_volume_ul: int | None = None
    module_kind: str | None = None


DEFINITIONS = {
    "nest_96_wellplate_200ul_flat": Definition("ABCDEFGH", 12, 200),
    "nest_12_reservoir_15ml": Definition("A", 12, 15000),
    "nest_96_wellplate_100ul_pcr_full_skirt": Definition("ABCDEFGH", 12, 100),
    "opentrons_96_aluminumblock_nest_wellplate_100ul": Definition(
        "ABCDEFGH", 12, 100, module_kind="temperature"
    ),
    "opentrons_96_deep_well_adapter_nest_wellplate_2ml_deep": Definition(
        "ABCDEFGH", 12, 2000, module_kind="heater_shaker"
    ),
    "opentrons_96_tiprack_20ul": Definition("ABCDEFGH", 12, 20, tip_volume_ul=20),
    "opentrons_96_tiprack_300ul": Definition("ABCDEFGH", 12, 300, tip_volume_ul=300),
    "opentrons_96_tiprack_1000ul": Definition("ABCDEFGH", 12, 1000, tip_volume_ul=1000),
}
PIPETTES = {
    "p20_single_gen2": (1, 20),
    "p300_single_gen2": (20, 300),
    "p1000_single_gen2": (100, 1000),
}
MODULE_LOAD_NAMES = {
    "temperature": "temperature module gen2",
    "heater_shaker": "heaterShakerModuleV1",
    "thermocycler": "thermocyclerModuleV2",
    "magnetic": "magnetic module gen2",
}
