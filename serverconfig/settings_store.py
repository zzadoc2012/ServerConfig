import json
from pathlib import Path
from typing import Dict, Optional

from serverconfig.paths import user_data_dir
from serverconfig.win_dpapi import protect, unprotect

ACCOUNT_KEYS = ("test_admin", "live_admin")

DEFAULT_ACCOUNTS = {
    "test_admin": {
        "name": "Test Admin",
        "address": "https://test-admin.phoenixdarts.com/",
        "user_id": "",
        "password": "",
    },
    "live_admin": {
        "name": "Live Admin",
        "address": "https://admin.phoenixdarts.com/",
        "user_id": "",
        "password": "",
    },
}


class SettingsStore:
    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = path or (user_data_dir() / "credentials.dat")
        self.accounts: Dict[str, dict] = json.loads(json.dumps(DEFAULT_ACCOUNTS))
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            return
        payload = unprotect(self.path.read_bytes())
        data = json.loads(payload.decode("utf-8"))
        accounts = data.get("accounts") or {}
        for key in ACCOUNT_KEYS:
            if key in accounts:
                self.accounts[key].update(accounts[key])

    def save(self) -> None:
        blob = json.dumps({"accounts": self.accounts}, ensure_ascii=False).encode("utf-8")
        self.path.write_bytes(protect(blob))

    def account(self, key: str) -> dict:
        return self.accounts[key]
