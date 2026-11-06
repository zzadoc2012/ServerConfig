import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from serverconfig.automation import merge_config, reset_config
from serverconfig.source_export import build_source_text


def main() -> None:
    existing = "#COIN_OPTION_FREE_PLAY=No\n$Coin:FreePlay=0\n"
    incoming = "#COIN_OPTION_FREE_PLAY=Yes"
    merged = merge_config(existing, incoming)
    assert "#COIN_OPTION_FREE_PLAY=No" not in merged
    assert "#COIN_OPTION_FREE_PLAY=Yes" in merged
    assert "$Coin:FreePlay=0" in merged
    assert merged.endswith("\n")

    empty = merge_config("", incoming)
    assert empty == "#COIN_OPTION_FREE_PLAY=Yes\n"

    same_key_twice = merge_config(
        "PxHistory:Enable=false\n",
        "PxHistory:Enable=true",
    )
    assert same_key_twice.count("PxHistory:Enable=") == 1
    assert "PxHistory:Enable=true" in same_key_twice

    cleared = reset_config("PxHistory:Enable=true\nCam:Use:Online=1\n$Coin:FreePlay=1\n")
    assert cleared == "Cam:Use:Online=1\n"
    assert reset_config("") == "Cam:Use:Online=1\n"
    dump = build_source_text()
    assert "def merge_config" in dump
    assert "class MainActivity" in dump
    print("merge_ok")


if __name__ == "__main__":
    main()
