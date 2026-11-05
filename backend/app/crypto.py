"""Encryption for stored provider credentials (§1.2, §20). Fernet (AES-128-CBC + HMAC-SHA256)."""

from __future__ import annotations

import json

from cryptography.fernet import Fernet, InvalidToken


class MasterKeyMissing(RuntimeError):
    pass


class Vault:
    def __init__(self, master_key: str) -> None:
        if not master_key:
            raise MasterKeyMissing("PAYTIENCE_MASTER_KEY not set — run `make keys`")
        self._f = Fernet(master_key.encode())

    def seal(self, values: dict[str, str]) -> str:
        return self._f.encrypt(json.dumps(values, sort_keys=True).encode()).decode()

    def open(self, token: str) -> dict[str, str]:
        try:
            data = json.loads(self._f.decrypt(token.encode()))
        except InvalidToken as e:
            raise ValueError("stored credential cannot be decrypted (master key changed?)") from e
        if not isinstance(data, dict):
            raise ValueError("corrupt credential payload")
        return {str(k): str(v) for k, v in data.items()}


def new_master_key() -> str:
    return Fernet.generate_key().decode()


def hint(value: str) -> str:
    """Masked display: never more than the last 4 chars, and only for values >= 12 chars."""
    return "••••" + value[-4:] if len(value) >= 12 else "••••"
