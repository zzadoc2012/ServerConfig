import json
from pathlib import Path
from typing import Dict, List, Optional

from serverconfig.paths import data_file

TYPE_TO_COLUMN = {
    "VSS": "VSS/VSP",
    "VSP": "VSS/VSP",
    "VSS/VSP": "VSS/VSP",
    "S4": "S4",
    "VSX": "VSX",
    "MAX": "MAX",
}

CHECKBOX_TYPES = ("VSS/VSP", "S4", "VSX", "MAX")


def load_machines(path: Optional[Path] = None) -> List[dict]:
    target = path or data_file("machines.json")
    with target.open(encoding="utf-8") as handle:
        machines = json.load(handle)
    for item in machines:
        raw = item.get("Location", item.get("name", ""))
        item["Location"] = _clean_location(raw)
        item.pop("name", None)
    return machines


def _clean_location(value) -> str:
    text = "" if value is None else str(value).strip()
    if text.startswith("("):
        text = text[1:].strip()
    if text.endswith(")"):
        text = text[:-1].strip()
    return text


def machine_location(item: dict) -> str:
    return _clean_location(item.get("Location", item.get("name", "")))


def machine_label(item: dict) -> str:
    base = f"{item['type']} {item['code']}"
    location = machine_location(item)
    if not location:
        return base
    return f"{base}   ({location})"


def machine_map(machines: List[dict]) -> Dict[str, dict]:
    return {item["code"]: item for item in machines}


def checkbox_type(machine_type: str) -> str:
    if machine_type in ("VSS", "VSP"):
        return "VSS/VSP"
    return machine_type


def excel_column(machine_type: str) -> str:
    return TYPE_TO_COLUMN[machine_type]
