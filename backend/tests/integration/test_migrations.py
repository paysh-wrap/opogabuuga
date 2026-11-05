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
    r = subprocess.run(
        [sys.executable, "-m", "alembic", "check"], cwd=BACKEND, env=env, capture_output=True, text=True, check=False
    )
    assert r.returncode == 0, r.stdout + r.stderr  # models and migrations agree
