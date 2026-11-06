#!/bin/bash
S=/tmp/claude-0/-home-user-opogabuuga/12967c39-053c-5693-bc8f-8a86efafe39e/scratchpad
cd /home/user/opogabuuga
until [ -f $S/long4/merged.json ]; do sleep 5; done
.venv/bin/python docs/results/tools/indscreen.py $S/long4/merged.json $S/mgc_v.csv 0.10 1.00 1.60 1.75 0.6 > $S/ind175.txt 2>&1
.venv/bin/python docs/results/tools/indscreen.py $S/long4/merged.json $S/mgc_v.csv 0.10 1.00 1.60 1.0 0.6 > $S/ind100.txt 2>&1
cd backend
for v in base vwap ut ema vwapema; do
  ../.venv/bin/python scripts/backtest.py $S/eng/mgc_2026-07.csv $S/eng/mgc_2026-08.csv $S/eng/mgc_2026-09.csv $S/eng/mgc_2026-10.csv --symbol MGC --plan $S/t_$v.yaml --jobs 4 > $S/eng_$v.json 2>&1
done
echo chain-done > $S/chain.done
