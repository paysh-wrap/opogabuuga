import pytest

from app.crypto import MasterKeyMissing, Vault, hint, new_master_key


def test_roundtrip_and_wrong_key():
    v = Vault(new_master_key())
    tok = v.seal({"api_key": "sk-secret-123456"})
    assert "sk-secret" not in tok
    assert v.open(tok) == {"api_key": "sk-secret-123456"}
    with pytest.raises(ValueError):
        Vault(new_master_key()).open(tok)


def test_missing_key():
    with pytest.raises(MasterKeyMissing):
        Vault("")


def test_hint_never_leaks_short_values():
    assert hint("abc") == "••••"
    assert hint("sk-abcdefgh1234") == "••••1234"
