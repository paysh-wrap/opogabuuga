from app import cli
from app.auth import authenticate
from app.db import Base, make_engine, make_sessionmaker
from app.settings import get_settings


def test_create_and_rename_admin(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'c.db'}"
    monkeypatch.setenv("PAYTIENCE_DATABASE_URL", url)
    monkeypatch.setenv("CI", "1")
    get_settings.cache_clear()
    try:
        monkeypatch.setenv("PAYTIENCE_ADMIN_PASSWORD", "long-enough-password")
        assert cli.main(["create-admin"]) == 0  # default user is PayDay
        assert cli.main(["rename-user", "PayDay", "Other"]) == 0
        assert cli.main(["rename-user", "Nobody", "X"]) == 1
        eng = make_engine(url)
        Base.metadata.create_all(eng)
        with make_sessionmaker(eng)() as s:
            assert authenticate(s, "Other", "long-enough-password") is not None
            assert authenticate(s, "PayDay", "long-enough-password") is None
        eng.dispose()
        assert cli.DEFAULT_ADMIN == "PayDay"
    finally:
        get_settings.cache_clear()
