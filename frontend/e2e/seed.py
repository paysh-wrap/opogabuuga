"""E2E-only seeding of the THROWAWAY scratch database (refuses anything else). Never used on data/paytience.db.

  seed.py cooldown              → MNQ TIGHT model-fail cooldown (3 failures) active for 5 sessions
  seed.py preflight             → test fixtures for pre-flight: this week's calendar (no events) + today's bias row
                                  (version "e2e-fixture") — run BEFORE the server starts (calendar cache is read at boot)
  seed.py profit <id> <usd> <locked 0|1> → record a closed winning trade this week (optionally lock the MLL)
"""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal

url = os.environ.get("PAYTIENCE_DATABASE_URL", "")
if "paytience-e2e-" not in url or url.endswith("data/paytience.db"):
    raise SystemExit(f"refusing to seed a non-scratch database: {url!r}")

from app.db import make_engine  # noqa: E402
from app.models import Account, Cooldown, Trade  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402


def main(argv: list[str]) -> None:
    eng = make_engine(url)
    now = datetime.now(UTC)
    with Session(eng) as s:
        if argv[0] == "preflight":
            from app.automation.state import set_setting
            from app.clock import session_date
            from app.models import BiasDecision

            set_setting(s, "calendar.cache", {"fetched_at": now.isoformat(), "error": None, "events": []}, now)
            for proxy in ("QQQ", "SPY", "DIA", "GLD"):
                s.add(BiasDecision(session_date=session_date(now), proxy=proxy, raw_rating="HOLD", mapped="NEUTRAL",
                                   reasoning="E2E test fixture", version="e2e-fixture"))
        elif argv[0] == "cooldown":
            s.add(Cooldown(symbol="MNQ", profile="TIGHT", streak=3, until_session=(now + timedelta(days=7)).date()))
        elif argv[0] == "profit":
            a = s.get(Account, int(argv[1]))
            assert a is not None
            if argv[3] == "1":
                a.mll_locked, a.mll = True, Decimal(25100)
            s.add(
                Trade(
                    account_id=a.id, symbol="MNQ", direction="LONG", qty=1, entry=Decimal(20000), exit=Decimal(20550),
                    risk_usd=Decimal(100), pnl_usd=Decimal(argv[2]), net_r=Decimal(1), opened_at=now - timedelta(minutes=5),
                    closed_at=now - timedelta(minutes=1), mode="PAPER", exit_reason="TP",
                )
            )
        else:
            raise SystemExit("unknown command")
        s.commit()


if __name__ == "__main__":
    main(sys.argv[1:])
