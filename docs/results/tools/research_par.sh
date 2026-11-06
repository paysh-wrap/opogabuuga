#!/bin/bash
# Parallel research export over a long 1m CSV: splits into monthly chunks (+7 days warm-up), runs research.py on
# each with 4 workers, then merges (keeping only setups whose session falls in the chunk's own month).
# usage: research_par.sh SYMBOL CSV PLAN OUTDIR START_YYYY-MM END_YYYY-MM
set -e
SYM=$1; CSV=$(realpath $2); PLAN=$(realpath $3); OUT=$(realpath -m $4); A=$5; B=$6
mkdir -p $OUT; T=$(dirname $(realpath $0))
python3 - "$CSV" "$OUT" "$A" "$B" <<'PY'
import sys, datetime as dt
csv, out, a, b = sys.argv[1:]
y, m = map(int, a.split("-")); ye, me = map(int, b.split("-"))
lines = open(csv).read().splitlines(); head, rows = lines[0], lines[1:]
while (y, m) <= (ye, me):
    s = dt.date(y, m, 1); e = dt.date(y + (m == 12), m % 12 + 1, 1); w = s - dt.timedelta(days=7)
    sel = [r for r in rows if w.isoformat() <= r[:10] < e.isoformat()]
    if sel:
        open(f"{out}/{s:%Y-%m}.csv", "w").write(head + "\n" + "\n".join(sel) + "\n")
    y, m = (y + 1, 1) if m == 12 else (y, m + 1)
PY
cd $T/../../../backend
ls $OUT/*.csv | xargs -P 4 -I{} sh -c "../.venv/bin/python $T/research.py $SYM {} $PLAN {}.json > {}.log 2>&1"
../.venv/bin/python - "$OUT" "$SYM" <<'PY'
import json, glob, sys
out, sym = sys.argv[1:]; sig = []
for f in sorted(glob.glob(f"{out}/*.csv.json")):
    mon = f.split("/")[-1][:7]; d = json.load(open(f))
    sig += [s for s in d["signals"] if str(s.get("entry_bar_time") or s.get("bar_time"))[:7] == mon]
json.dump({"symbol": sym, "signals": sig}, open(f"{out}/merged.json", "w"), default=str)
print("merged", len(sig), "signals")
PY
