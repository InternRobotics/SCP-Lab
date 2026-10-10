"""Deterministic preflight and nominal liquid accounting, independent of the SDK."""

from .labware import DEFINITIONS, PIPETTES
from .models import Consolidate, Distribute, Mix, Protocol, ThermalCycle, Transfer, WellRef


def transfers(step):
    if isinstance(step, Transfer):
        return [(step.source, step.destination, step.volume_ul)]
    if isinstance(step, Distribute):
        return [(step.source, d, step.volume_per_destination_ul) for d in step.destinations]
    if isinstance(step, Consolidate):
        return [(s, step.destination, step.volume_per_source_ul) for s in step.sources]
    return []


def validate(protocol: Protocol) -> dict:
    labware = {x.id: x for x in protocol.setup.labware}
    modules = {x.id: x for x in protocol.setup.modules}
    all_ids = [x.id for x in protocol.setup.labware + protocol.setup.modules]
    if len(set(all_ids)) != len(all_ids):
        raise ValueError("Labware and module IDs must be unique")
    if len({s.id for s in protocol.steps}) != len(protocol.steps):
        raise ValueError("Step IDs must be unique")
    occupied = {}

    def occupy(slot, name):
        if slot in occupied:
            raise ValueError(f"Deck slot {slot} conflict: {occupied[slot]} and {name}")
        occupied[slot] = name

    for m in modules.values():
        if m.kind == "thermocycler":
            if m.slot != 7:
                raise ValueError("Thermocycler must use slot 7 (occupies 7, 8, 10, 11)")
            for slot in (7, 8, 10, 11):
                occupy(slot, m.id)
        else:
            if m.kind == "heater_shaker" and m.slot not in (1, 3, 4, 6, 7, 10):
                raise ValueError("Unsupported Heater-Shaker slot")
            occupy(m.slot, m.id)

    module_labware = set()
    for lw in labware.values():
        if lw.load_name not in DEFINITIONS:
            raise ValueError(f"Labware {lw.load_name!r} is outside the reviewed subset")
        definition = DEFINITIONS[lw.load_name]
        if lw.location in modules:
            if lw.location in module_labware:
                raise ValueError("Only one labware item per module is supported")
            module_labware.add(lw.location)
            kind = modules[lw.location].kind
            compatible = definition.module_kind == kind or (
                kind in ("magnetic", "thermocycler")
                and lw.load_name == "nest_96_wellplate_100ul_pcr_full_skirt"
            )
            if not compatible:
                raise ValueError(f"Unsupported labware/module combination: {lw.id}, {kind}")
        else:
            if lw.location not in {str(i) for i in range(1, 12)}:
                raise ValueError(f"Unknown location: {lw.location}")
            if definition.module_kind:
                raise ValueError(f"{lw.id} requires a {definition.module_kind} module")
            occupy(int(lw.location), lw.id)

    # Conservatively reserve adjacent slots; broader layouts require SDK-specific review.
    for m in modules.values():
        if m.kind == "heater_shaker":
            neighbors = (m.slot + 1,) if m.slot % 3 == 1 else (m.slot - 1,)
            for slot in neighbors:
                if slot in occupied:
                    raise ValueError(f"Keep adjacent Heater-Shaker slot {slot} empty")

    pipette = protocol.setup.pipette
    tip_capacity = 0
    if pipette:
        if len(set(pipette.tip_racks)) != len(pipette.tip_racks):
            raise ValueError("Duplicate tip rack reference")
        for tip_id in pipette.tip_racks:
            if tip_id not in labware:
                raise ValueError(f"Unknown tip rack: {tip_id}")
            lw = labware[tip_id]
            definition = DEFINITIONS[lw.load_name]
            if definition.tip_volume_ul != PIPETTES[pipette.model][1]:
                raise ValueError(f"Tip rack {tip_id} does not match {pipette.model}")
            tip_capacity += len(definition.rows) * definition.columns

    def well(ref: WellRef):
        if ref.labware not in labware:
            raise ValueError(f"Unknown labware: {ref.labware}")
        definition = DEFINITIONS[labware[ref.labware].load_name]
        if (
            definition.tip_volume_ul
            or ref.well[0] not in definition.rows
            or int(ref.well[1:]) > definition.columns
        ):
            raise ValueError(f"Invalid liquid well: {ref.labware}/{ref.well}")
        return f"{ref.labware}/{ref.well}", definition.capacity_ul

    volumes, origins = {}, {}
    for liquid in protocol.liquids:
        key, capacity = well(liquid.location)
        if key in volumes:
            raise ValueError(f"Duplicate initial liquid at {key}")
        if liquid.volume_ul > capacity:
            raise ValueError(f"Initial liquid exceeds capacity at {key}")
        volumes[key] = liquid.volume_ul
        origins[key] = {liquid.sample_id}

    def pipette_volume(volume):
        if not pipette:
            raise ValueError("Pipetting steps require a configured pipette")
        low, high = PIPETTES[pipette.model]
        if not low <= volume <= high:
            raise ValueError(
                f"Volume {volume} uL is outside the configured pipette range {low}–{high}"
            )

    tips = 0
    events = []
    for step in protocol.steps:
        for source, destination, volume in transfers(step):
            pipette_volume(volume)
            src, _ = well(source)
            dst, capacity = well(destination)
            if src == dst:
                raise ValueError(f"Step {step.id}: source equals destination; use pipette_mixing")
            if volumes.get(src, 0) + 1e-8 < volume:
                raise ValueError(f"Step {step.id}: insufficient declared liquid at {src}")
            if volumes.get(dst, 0) + volume > capacity + 1e-8:
                raise ValueError(f"Step {step.id}: destination overflow at {dst}")
            parents = sorted(origins.get(src, set()))
            volumes[src] -= volume
            volumes[dst] = volumes.get(dst, 0) + volume
            origins.setdefault(dst, set()).update(parents)
            if volumes[src] < 1e-8:
                origins[src] = set()
            events.append(
                {
                    "step_id": step.id,
                    "source": src,
                    "destination": dst,
                    "volume_ul": volume,
                    "source_sample_ids": parents,
                    "evidence": "planned_not_measured",
                }
            )
            tips += 1
        if isinstance(step, Mix):
            pipette_volume(step.volume_ul)
            key, _ = well(step.sample)
            if volumes.get(key, 0) + 1e-8 < step.volume_ul:
                raise ValueError(f"Step {step.id}: mixing volume exceeds liquid at {key}")
            tips += 1
        required_module = {
            "incubation": "temperature",
            "orbital_shaking": "heater_shaker",
            "thermal_cycling": "thermocycler",
            "magnetic_separation": "magnetic",
        }.get(step.action)
        if required_module:
            lw = labware.get(step.labware)
            module = modules.get(lw.location) if lw else None
            if not module or module.kind != required_module:
                raise ValueError(f"Step {step.id}: labware must already be on {required_module}")
            if isinstance(step, ThermalCycle):
                current_max = max(
                    (v for k, v in volumes.items() if k.startswith(step.labware + "/")), default=0
                )
                if step.block_max_volume_ul < current_max:
                    raise ValueError("block_max_volume_ul is below the declared sample volume")
    if tips > tip_capacity:
        raise ValueError(f"Protocol needs {tips} fresh tips; only {tip_capacity} configured")
    return {
        "schema_version": "scp-lab.validation.v0.1",
        "valid": True,
        "validation_level": "static",
        "physical_execution": False,
        "step_count": len(protocol.steps),
        "required_tips": tips,
        "predicted_wells": [
            {
                "location": key,
                "volume_ul": round(volume, 8),
                "source_sample_ids": sorted(origins.get(key, set())),
            }
            for key, volume in sorted(volumes.items())
        ],
        "planned_transfers": events,
        "limitations": [
            "Volumes and sample ancestry are calculated from declared inputs, not measured.",
            "Dead volume, liquid properties, calibration and physical completion are not verified.",
            "Module labware is preloaded; this version does not move labware.",
        ],
    }
