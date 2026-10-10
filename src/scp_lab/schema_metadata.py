"""Small SCP-Lab JSON Schema annotations; no unit inference or automatic conversion."""

from jsonschema import Draft202012Validator


def schema_nodes(schema):
    """Visit schema locations only, never literal data in defaults, enums or examples."""
    if not isinstance(schema, dict):
        return
    yield schema
    for key in ("properties", "patternProperties", "$defs", "definitions", "dependentSchemas"):
        for child in schema.get(key, {}).values():
            yield from schema_nodes(child)
    for key in ("allOf", "anyOf", "oneOf", "prefixItems"):
        for child in schema.get(key, []):
            yield from schema_nodes(child)
    for key in (
        "items",
        "additionalProperties",
        "unevaluatedProperties",
        "unevaluatedItems",
        "contains",
        "propertyNames",
        "if",
        "then",
        "else",
        "not",
    ):
        yield from schema_nodes(schema.get(key))


def check_schema(schema: dict) -> None:
    Draft202012Validator.check_schema(schema)
    for node in schema_nodes(schema):
        if "x-scp-unit" in node:
            unit = node["x-scp-unit"]
            if not isinstance(unit, str) or not unit.strip():
                raise ValueError("x-scp-unit must be a nonempty, documented unit string")


def annotate_source_units(schema: dict) -> list[str]:
    """Annotate only unambiguous unit phrases actually present in supplied device schemas."""
    phrases = {
        " in uL.": "uL",
        " in nm.": "nm",
        " in mm.": "mm",
        " in rpm.": "rpm",
        " in seconds.": "s",
        " in °C.": "degC",
        " in Celsius.": "degC",
        " in mbar.": "mbar",
        " in ppm.": "ppm",
        " in %.": "%",
    }
    limitations = []
    for node in schema_nodes(schema):
        description = node.get("description", "")
        if "in uL or mL" in description:
            message = (
                "Source volume description says 'uL or mL' but provides no unit selector. "
                "No canonical unit or conversion is assumed; only the declared schema is validated."
            )
            if message not in limitations:
                limitations.append(message)
            continue
        for phrase, unit in phrases.items():
            if phrase in description:
                node["x-scp-unit"] = unit
        if description in {"Acceleration percent.", "Deceleration percent."}:
            node["x-scp-unit"] = "%"
    return limitations
