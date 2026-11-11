import sqlite3
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]


def test_alembic_upgrade_creates_schema_and_append_only_audit(tmp_path):
    db = tmp_path / "m.db"
    env = {"PAYTIENCE_DATABASE_URL": f"sqlite:///{db}", "PATH": "/usr/bin:/bin"}
    r = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr
    con = sqlite3.connect(db)
    names = {n for (n,) in con.execute("select name from sqlite_master")}
    assert {
        "accounts",
        "signals",
        "trades",
        "audit_log",
        "api_credentials",
        "audit_no_update",
        "audit_no_delete",
    } <= names
    con.execute(
        "insert into audit_log(at,actor,action,entity,payload,prev_hash,hash) "
        "values('2026-01-01','a','b','', '{}','0','1')"
    )
    try:
        con.execute("delete from audit_log")
        raise AssertionError("delete should be blocked")
    except sqlite3.DatabaseError as e:
        assert "append-only" in str(e)
    finally:
        con.close()
    r = subprocess.run(
        [sys.executable, "-m", "alembic", "check"], cwd=BACKEND, env=env, capture_output=True, text=True, check=False
    )
    assert r.returncode == 0, r.stdout + r.stderr  # models and migrations agree


def test_migration_drops_stored_telegram_credential_only(tmp_path):  # D90
    db = tmp_path / "t.db"
    env = {"PAYTIENCE_DATABASE_URL": f"sqlite:///{db}", "PATH": "/usr/bin:/bin"}

    def alembic(target: str) -> None:
        r = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", target],
            cwd=BACKEND,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert r.returncode == 0, r.stderr

    alembic("c5d9e3f7a2b4")
    con = sqlite3.connect(db)
    for pid in ("telegram", "discord"):
        con.execute(
            "insert into api_credentials(provider,ciphertext,hints,status,status_detail,updated_at,created_at) "
            "values(?,'x','{}','saved','','2026-01-01','2026-01-01')",
            (pid,),
        )
    con.commit()
    con.close()
    alembic("head")
    con = sqlite3.connect(db)
    assert [p for (p,) in con.execute("select provider from api_credentials")] == ["discord"]
