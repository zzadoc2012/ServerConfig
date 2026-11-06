import sys
from pathlib import Path
from typing import Iterable, Optional

from serverconfig.paths import app_dir, bundled_dir

DUMP_NAME = "ServerConfig-source.txt"

SOURCE_FILES = (
    "README.md",
    "requirements.txt",
    "ServerConfig.spec",
    "main.py",
    "serverconfig/__init__.py",
    "serverconfig/gui.py",
    "serverconfig/automation.py",
    "serverconfig/excel_loader.py",
    "serverconfig/machines.py",
    "serverconfig/paths.py",
    "serverconfig/settings_store.py",
    "serverconfig/source_export.py",
    "serverconfig/worker.py",
    "serverconfig/win_dpapi.py",
    "tests/test_excel.py",
    "tests/test_merge.py",
    "tools/export_source.py",
    "tools/sync_dist_data.py",
    "data/configs.json",
    "data/machines.json",
    "android/settings.gradle.kts",
    "android/build.gradle.kts",
    "android/gradle.properties",
    "android/gradle/wrapper/gradle-wrapper.properties",
    "android/app/build.gradle.kts",
    "android/app/proguard-rules.pro",
    "android/app/src/main/AndroidManifest.xml",
    "android/app/src/main/java/com/phoenixdarts/serverconfig/MainActivity.kt",
    "android/app/src/main/java/com/phoenixdarts/serverconfig/AdminClient.kt",
    "android/app/src/main/java/com/phoenixdarts/serverconfig/AssetRepository.kt",
    "android/app/src/main/java/com/phoenixdarts/serverconfig/ConfigMerge.kt",
    "android/app/src/main/java/com/phoenixdarts/serverconfig/Models.kt",
    "android/app/src/main/java/com/phoenixdarts/serverconfig/SettingsStore.kt",
    "android/app/src/main/res/layout/activity_main.xml",
    "android/app/src/main/res/layout/dialog_add_config.xml",
    "android/app/src/main/res/layout/dialog_settings.xml",
    "android/app/src/main/res/values/colors.xml",
    "android/app/src/main/res/values/strings.xml",
    "android/app/src/main/res/values/themes.xml",
    "android/app/src/main/res/drawable/ic_launcher.xml",
    "android/app/src/main/assets/configs.json",
    "android/app/src/main/assets/machines.json",
)


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def bundled_dump() -> Path:
    sidecar = app_dir() / DUMP_NAME
    if sidecar.exists():
        return sidecar
    return bundled_dir() / "data" / DUMP_NAME


def build_source_text(root: Optional[Path] = None, files: Iterable[str] = SOURCE_FILES) -> str:
    base = root or project_root()
    chunks = ["ServerConfig 소스 모음", ""]
    missing = []
    for relative in files:
        path = base / relative
        chunks.append("=" * 72)
        chunks.append("# " + relative.replace("\\", "/"))
        chunks.append("=" * 72)
        if not path.exists():
            missing.append(relative)
            chunks.append("(missing)\n")
            continue
        text = path.read_text(encoding="utf-8")
        chunks.append(text if text.endswith("\n") else text + "\n")
        chunks.append("")
    if missing:
        raise FileNotFoundError("소스 파일이 없습니다: " + ", ".join(missing))
    return "\n".join(chunks)


def source_text() -> str:
    if getattr(sys, "frozen", False):
        dump = bundled_dump()
        if not dump.exists():
            raise FileNotFoundError(DUMP_NAME)
        return dump.read_text(encoding="utf-8")
    return build_source_text()


def write_source_dump(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source_text(), encoding="utf-8")
    return path
