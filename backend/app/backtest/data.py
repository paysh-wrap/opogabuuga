"""Historical 1-minute bars from a CSV file (e.g. downloaded from the Databento portal: GLBX.MDP3, ohlcv-1m).

Accepted columns (case-insensitive): a time column (ts_event | timestamp | time | datetime | date) holding either an
ISO-8601 time or integer epoch nanoseconds/milliseconds/seconds, plus open, high, low, close and optional volume.
The time is the bar OPEN. Prices may be decimals; fixed-point integers (price × 1e9, Databento without pretty_px)
are detected when far above any plausible futures price and scaled back. Optional `symbol` column filters rows.
"""

from __future__ import annotations

import csv
import io
from datetime import UTC, datetime
from decimal import Decimal

from app.indicators.bars import Bar

TIME_COLS = ("ts_event", "timestamp", "time", "datetime", "date")
FIXED = Decimal(1_000_000_000)


class DataError(ValueError):
    pass


def _ms(raw: str) -> int:
    s = raw.strip()
    if s.lstrip("-").isdigit():
        n = int(s)
        if n > 10**17:
            return n // 1_000_000  # ns
        if n > 10**14:
            return n // 1_000  # µs
        if n > 10**11:
            return n  # ms
        return n * 1000  # s
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise DataError(f"time without timezone: {raw!r} (use UTC, e.g. 2026-01-05T14:30:00Z)")
    return int(dt.astimezone(UTC).timestamp() * 1000)


def load_csv(text: str, symbol_contains: str | None = None, minutes: int = 1) -> list[Bar]:
    rd = csv.DictReader(io.StringIO(text))
    if not rd.fieldnames:
        raise DataError("empty CSV")
    cols = {c.lower().strip(): c for c in rd.fieldnames}
    tcol = next((cols[c] for c in TIME_COLS if c in cols), None)
    need = [c for c in ("open", "high", "low", "close") if c not in cols]
    if tcol is None or need:
        raise DataError(f"CSV needs a time column {TIME_COLS} and open/high/low/close (missing: {need or 'time'})")
    out: dict[int, Bar] = {}
    for row in rd:
        if symbol_contains and "symbol" in cols and symbol_contains not in row[cols["symbol"]]:
            continue
        o, h, lo, c = (Decimal(row[cols[k]]) for k in ("open", "high", "low", "close"))
        if o > FIXED:
            o, h, lo, c = (x / FIXED for x in (o, h, lo, c))
        if not lo <= min(o, c) <= max(o, c) <= h:
            raise DataError(f"bad OHLC row: {row}")
        t = _ms(row[tcol])
        v = Decimal(row[cols["volume"]]) if "volume" in cols and row[cols["volume"]] else Decimal(0)
        out[t] = Bar(t, t + minutes * 60_000, o, h, lo, c, v)
    if not out:
        raise DataError("no rows")
    return [out[k] for k in sorted(out)]
