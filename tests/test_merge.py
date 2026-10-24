import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from serverconfig.automation import merge_config


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
    print("merge_ok")


if __name__ == "__main__":
    main()
