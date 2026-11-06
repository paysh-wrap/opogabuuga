"""Win rate vs target size on the SAME candidate entries/stops (exported by research.py).
For each target k·R: limit entry as the engine does, stop-first, 1-tick stop slip, fees, flat 16:40 ET.
usage: frontier.py RES.json CSV TICK TICK_VALUE FEE_RT [hours e.g. 5-7,9-12,13-15]"""
import bisect
import json
import sys
from datetime import UTC, datetime, time
from decimal import Decimal as D
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, "/home/user/paytience/backend")
from app.backtest.data import load_csv  # noqa: E402
from app.clock import session_date  # noqa: E402

ET = ZoneInfo("America/New_York")
res = json.load(open(sys.argv[1]))
bars = load_csv(Path(sys.argv[2]).read_text())
TICK, TV, FEE = D(sys.argv[3]), D(sys.argv[4]), D(sys.argv[5])
HOURS = None
if len(sys.argv) > 6:
    HOURS = []
    for part in sys.argv[6].split(","):
        a, b = part.split("-")
        HOURS.append((int(a), int(b)))
opens = [b.open_ms for b in bars]
KS = [D("1.0"), D("1.25"), D("1.5"), D("1.75"), D("2.0"), D("2.5"), D("3.0")]


def ts(s):
    d = datetime.fromisoformat(str(s).replace(" ", "T"))
    return d if d.tzinfo else d.replace(tzinfo=UTC)


def run(c, k, use_t2_cap):
    p = next((x for x in c["plans"] if x["mode"] == "STANDARD"), None)
    if p is None:
        return None
    d = 1 if p["direction"] == "LONG" else -1
    entry, stop, risk = D(p["entry"]), D(p["stop"]), D(p["risk_pts"])
    tp = entry + d * k * risk
    if use_t2_cap:
        t2 = D(c["features"]["t2"])
        if (t2 - entry) * d < k * risk:
            return "SKIP"  # the model's T2 does not reach this target → the engine would skip (RR_BELOW_MIN)
    t0 = ts(c["entry_bar_time"] or c["bar_time"])
    tf = 5 if c["profile"] == "STD" else 1
    i = bisect.bisect_left(opens, int(t0.timestamp() * 1000))
    deadline = int(t0.timestamp() * 1000) + 4 * tf * 60_000
    fill = None
    while i < len(bars) and bars[i].open_ms < deadline:
        b = bars[i]
        if (d == 1 and b.l <= entry) or (d == -1 and b.h >= entry):
            fill = i
            break
        i += 1
    if fill is None:
        return None
    fee_r = FEE / (risk / TICK * TV)
    for j in range(fill, len(bars)):
        b = bars[j]
        if j > fill and datetime.fromtimestamp(b.open_ms / 1000, tz=UTC).astimezone(ET).time() >= time(16, 40):
            r = (b.o - entry) * d / risk - fee_r
            return float(r)
        if (d == 1 and b.l <= stop) or (d == -1 and b.h >= stop):
            return float(D(-1) - TICK / risk - fee_r)
        if j > fill and ((d == 1 and b.h >= tp) or (d == -1 and b.l <= tp)):
            return float(k - fee_r)
    return 0.0


cands = []
for c in res["signals"]:
    if c["status"] != "PASS" or not c["plans"]:
        continue
    h = ts(c["entry_bar_time"] or c["bar_time"]).astimezone(ET).hour
    if HOURS and not any(a <= h < b for a, b in HOURS):
        continue
    cands.append(c)
days = sorted({session_date(ts(c["entry_bar_time"] or c["bar_time"])) for c in cands})
cut = days[int(len(days) * 0.73)] if days else None
label = f"hours {sys.argv[6]}" if HOURS else "all hours"
print(f"{res['symbol']} — {label}: {len(cands)} setups over {len(days)} sessions (target = k × risk; stop unchanged)")
for cap in (False, True):
    print("  " + ("only setups whose model T2 reaches the target (as the engine requires)" if cap else "any target (ignores T2)"))
    for k in KS:
        out = {"train": [], "test": []}
        for c in cands:
            r = run(c, k, cap)
            if r is None or r == "SKIP":
                continue
            part = "train" if session_date(ts(c["entry_bar_time"] or c["bar_time"])) < cut else "test"
            out[part].append(r)
        row = []
        for part in ("train", "test"):
            rs = out[part]
            n = len(rs)
            w = sum(1 for r in rs if r > 0)
            row.append(f"{n:3d} tr {w / n * 100:3.0f}% {sum(rs) / n:+.2f}R" if n else "  0 tr")
        print(f"    {k:>4}R   train {row[0]} | test {row[1]}")
