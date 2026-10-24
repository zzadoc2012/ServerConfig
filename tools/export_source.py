from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "dist" / "ServerConfig-source.txt"
SOURCE_FILES = (
    "main.py",
    "requirements.txt",
    "serverconfig/__init__.py",
    "serverconfig/gui.py",
    "serverconfig/automation.py",
    "serverconfig/excel_loader.py",
    "serverconfig/machines.py",
    "serverconfig/paths.py",
    "serverconfig/settings_store.py",
    "serverconfig/worker.py",
    "serverconfig/win_dpapi.py",
)


def main() -> None:
    chunks = ["ServerConfig 소스 모음", ""]
    for relative in SOURCE_FILES:
        path = ROOT / relative
        chunks.append("=" * 72)
        chunks.append("# " + relative)
        chunks.append("=" * 72)
        chunks.append(path.read_text(encoding="utf-8"))
        if not chunks[-1].endswith("\n"):
            chunks.append("")
        chunks.append("")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(chunks), encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
