import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from serverconfig.source_export import DUMP_NAME, build_source_text


def main() -> None:
    text = build_source_text(ROOT)
    targets = (
        ROOT / "dist" / DUMP_NAME,
        ROOT / "dist" / "ServerConfig" / DUMP_NAME,
    )
    for target in targets:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        print(target)


if __name__ == "__main__":
    main()
