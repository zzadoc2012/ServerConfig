import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from openpyxl import load_workbook

from serverconfig.paths import app_dir, data_file

TYPE_HEADERS = ("VSS/VSP", "S4", "VSX", "MAX")


class ConfigWorkbook:
    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = path or data_file("config.xlsx")
        self.names: List[str] = []
        self.rows: Dict[str, Dict[str, str]] = {}
        self.reload()

    def reload(self) -> None:
        if not self.path.exists():
            raise FileNotFoundError(str(self.path))
        workbook = load_workbook(self.path, data_only=True)
        try:
            sheet = workbook.active
            header_map = self._header_map(next(sheet.iter_rows(min_row=1, max_row=1, values_only=True)))
            names: List[str] = []
            rows: Dict[str, Dict[str, str]] = {}
            for values in sheet.iter_rows(min_row=2, values_only=True):
                name = self._cell(values, header_map["Config Name"], command=False)
                if not name:
                    continue
                names.append(name)
                rows[name] = {
                    header: self._cell(values, header_map[header], command=True) for header in TYPE_HEADERS
                }
            if not names:
                raise ValueError("Config Name 행을 찾지 못했습니다.")
            self.names = names
            self.rows = rows
        finally:
            workbook.close()

    def value(self, config_name: str, column: str) -> Tuple[str, bool]:
        if config_name not in self.rows:
            raise KeyError(config_name)
        if column not in self.rows[config_name]:
            raise KeyError(column)
        raw = self.rows[config_name][column]
        return raw, raw != ""

    def names_for_column(self, column: str) -> List[str]:
        names = []
        for name in self.names:
            _value, has_value = self.value(name, column)
            if has_value:
                names.append(name)
        return names

    def add(self, name: str, values: Dict[str, str]) -> None:
        name = (name or "").strip()
        if not name:
            raise ValueError("Config Name을 입력하세요.")
        if name in self.rows:
            raise ValueError("같은 Config Name이 이미 있습니다.")
        cleaned = {header: normalize_config_text(values.get(header, "")) for header in TYPE_HEADERS}
        if not any(cleaned.values()):
            raise ValueError("VSS/VSP, S4, VSX, MAX 중 하나 이상 입력하세요.")
        self._ensure_writable()
        workbook = load_workbook(self.path)
        try:
            sheet = workbook.active
            header_map = self._header_map(next(sheet.iter_rows(min_row=1, max_row=1, values_only=True)))
            row_idx = sheet.max_row + 1
            sheet.cell(row_idx, header_map["Config Name"] + 1, name)
            for header in TYPE_HEADERS:
                sheet.cell(row_idx, header_map[header] + 1, cleaned[header])
            workbook.save(self.path)
        finally:
            workbook.close()
        self.reload()

    def _ensure_writable(self) -> None:
        sidecar = app_dir() / "data" / "config.xlsx"
        if self.path.resolve() == sidecar.resolve():
            return
        sidecar.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self.path, sidecar)
        self.path = sidecar

    @staticmethod
    def _header_map(header_row) -> Dict[str, int]:
        mapping = {}
        for index, value in enumerate(header_row or ()):
            text = "" if value is None else str(value).strip()
            if text:
                mapping[text] = index
        required = ("Config Name",) + TYPE_HEADERS
        missing = [name for name in required if name not in mapping]
        if missing:
            raise ValueError("엑셀 헤더가 규격과 다릅니다: " + ", ".join(missing))
        return mapping

    @staticmethod
    def _cell(values, index: int, command: bool = False) -> str:
        if index >= len(values) or values[index] is None:
            return ""
        text = str(values[index]).replace("\r\n", "\n")
        if not command:
            return text.strip()
        return normalize_config_text(text)


def normalize_config_text(text: str) -> str:
    lines = (text or "").replace("\r\n", "\n").split("\n")
    cleaned = [line.strip() for line in lines]
    while cleaned and cleaned[0] == "":
        cleaned.pop(0)
    while cleaned and cleaned[-1] == "":
        cleaned.pop()
    return "\n".join(cleaned)
