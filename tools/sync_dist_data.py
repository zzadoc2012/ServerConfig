"""Copy repo data files next to the exe without replacing operational lists."""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data"
DST = ROOT / "dist" / "ServerConfig" / "data"
OLD = ROOT / "dist" / "data"
SKIP_IF_EXISTS = {"config.xlsx", "machines.json"}


def main() -> None:
    DST.mkdir(parents=True, exist_ok=True)
    if OLD.exists():
        for src in OLD.iterdir():
            if not src.is_file() or src.name.startswith("~$"):
                continue
            if not (DST / src.name).exists():
                shutil.copy2(src, DST / src.name)
                print("seeded", DST / src.name)
    for src in SRC.iterdir():
        if not src.is_file() or src.name.startswith("~$"):
            continue
        dest = DST / src.name
        if src.name in SKIP_IF_EXISTS and dest.exists():
            print("keep existing", dest)
            continue
        shutil.copy2(src, dest)
        print("copied", dest)


if __name__ == "__main__":
    main()
