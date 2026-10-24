import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from serverconfig.excel_loader import ConfigWorkbook
from serverconfig.machines import excel_column, load_machines


def main() -> None:
    machines = load_machines()
    assert machines[0]["code"] == "171"
    book = ConfigWorkbook(ROOT / "data" / "config.xlsx")
    assert "히스토리" in book.names[0] or "History" in book.names[0]
    history = book.names[0]
    freeplay = book.names[1]
    vss, ok = book.value(history, excel_column("VSS"))
    assert ok and "PxHistory:Enable=true" in vss
    vsx, ok = book.value(history, excel_column("VSX"))
    assert ok and "PhoenixHistoryMission:Enable:VSX=true" in vsx
    max_value, ok = book.value(history, excel_column("MAX"))
    assert ok and "PhoenixHistoryMission:Enable:MAX=true" in max_value
    s4, ok = book.value(history, excel_column("S4"))
    assert ok and "PxHistory:Enable=true" in s4
    free_vss, ok = book.value(freeplay, excel_column("VSS"))
    assert ok and "$Coin:FreePlay=1" in free_vss
    assert not free_vss.startswith("\t") and not free_vss.startswith(" ")
    assert free_vss.startswith("$Coin:FreePlay=1")
    free_vsx, ok = book.value(freeplay, excel_column("VSX"))
    assert ok and "COIN_OPTION_FREE_PLAY=Yes" in free_vsx
    vss_names = book.names_for_column(excel_column("VSS"))
    assert history in vss_names
    print("excel_ok", book.names, "vss", vss_names)


if __name__ == "__main__":
    main()
