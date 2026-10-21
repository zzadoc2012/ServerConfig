import json
from pathlib import Path
from typing import Dict, List, Optional

from serverconfig.paths import data_file

TYPE_TO_COLUMN = {
    "VSS": "VSS/VSP",
    "VSP": "VSS/VSP",
    "S4": "S4",
    "VSX": "VSX",
    "MAX": "MAX",
}

CHECKBOX_TYPES = ("VSS", "S4", "VSX", "MAX")


def load_machines(path: Optional[Path] = None) -> List[dict]:
    target = path or data_file("machines.json")
    with target.open(encoding="utf-8") as handle:
        return json.load(handle)


def machine_map(machines: List[dict]) -> Dict[str, dict]:
    return {item["code"]: item for item in machines}


def checkbox_type(machine_type: str) -> str:
    if machine_type == "VSP":
        return "VSS"
    return machine_type


def excel_column(machine_type: str) -> str:
    return TYPE_TO_COLUMN[machine_type]
