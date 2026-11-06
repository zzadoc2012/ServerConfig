import sys
from pathlib import Path


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def bundled_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS"))
    return app_dir()


def data_file(name: str) -> Path:
    sidecar = app_dir() / "data" / name
    if sidecar.exists():
        return sidecar
    return bundled_dir() / "data" / name


def user_data_dir() -> Path:
    root = Path.home() / "AppData" / "Roaming" / "ServerConfig"
    root.mkdir(parents=True, exist_ok=True)
    return root
