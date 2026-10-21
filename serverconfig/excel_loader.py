from pathlib import Path
from typing import Dict, List, Optional, Tuple

from openpyxl import load_workbook

from serverconfig.paths import data_file

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
                name = self._cell(values, header_map["Config Name"])
                if not name:
                    continue
                names.append(name)
                rows[name] = {header: self._cell(values, header_map[header]) for header in TYPE_HEADERS}
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
    def _cell(values, index: int) -> str:
        if index >= len(values) or values[index] is None:
            return ""
        return str(values[index]).replace("\r\n", "\n")
