from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DatabaseError, StatementError

from app import audit
from app.clock import FixedClock
from app.db import Base, make_engine, make_sessionmaker
from app.models import Account, AuditLog, Trade


@pytest.fixture
def sm(tmp_path):
    eng = make_engine(f"sqlite:///{tmp_path / 'a.db'}")
    Base.metadata.create_all(eng)
    yield make_sessionmaker(eng)
    eng.dispose()


CLK = FixedClock(datetime(2026, 11, 5, 15, tzinfo=UTC))


def test_decimal_roundtrip_exact(sm):
    with sm() as s:
        a = Account(broker_account_id="DEMO1", stage="EVAL", drawdown_type="eod", mll=Decimal("24000"))
        s.add(a)
        s.flush()
        t = Trade(
            account_id=a.id,
            symbol="MNQ",
            direction="LONG",
            qty=2,
            entry=Decimal("20000.75"),
            risk_usd=Decimal("186.90"),
            opened_at=CLK.now(),
        )
        s.add(t)
        s.commit()
        assert s.get(Account, a.id).mll == Decimal("24000")
        got = s.get(Trade, t.id)
        assert got.entry == Decimal("20000.75") and got.risk_usd == Decimal("186.90")


def test_float_rejected(sm):
    with sm() as s:
        s.add(
            Trade(
                account_id=1,
                symbol="MNQ",
                direction="LONG",
                qty=1,
                entry=20000.1,
                risk_usd=Decimal(1),
                opened_at=CLK.now(),
            )
        )
        with pytest.raises((TypeError, StatementError)):
            s.flush()


def test_audit_chain_and_append_only(sm):
    with sm() as s:
        for i in range(3):
            audit.record(s, CLK, "me", "test.action", "x", {"i": i, "amt": Decimal("1.50")})
        s.commit()
        assert audit.verify_chain(s) == (True, None)
        with pytest.raises(DatabaseError):
            s.execute(text("UPDATE audit_log SET actor='evil' WHERE id=2"))
        s.rollback()
        with pytest.raises(DatabaseError):
            s.execute(text("DELETE FROM audit_log WHERE id=1"))
        s.rollback()
        assert s.query(AuditLog).count() == 3


def test_audit_tamper_detected(sm):
    with sm() as s:
        for i in range(3):
            audit.record(s, CLK, "me", "a", "", {"i": i})
        s.commit()
        s.execute(text("DROP TRIGGER audit_no_update"))  # simulate an attacker with raw DB access
        s.execute(text("UPDATE audit_log SET payload='{\"i\": 99}' WHERE id=2"))
        s.commit()
        assert audit.verify_chain(s) == (False, 2)
