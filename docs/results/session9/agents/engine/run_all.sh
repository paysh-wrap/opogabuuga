set -x
cd /home/user/opogabuuga/backend
P=/home/user/opogabuuga/.venv/bin/python
for spec in "MNQ 2023 ^2023-" "MNQ oos ^(2025-1[12]|2026-)" "MGC 2023 ^2023-" "MGC oos ^(2025-1[12]|2026-)"; do
  set -- $spec; sym=$1; tag=$2; pat=$3; low=$(echo $sym | tr A-Z a-z)
  (head -1 /tmp/claude-0/-home-user-opogabuuga/586832a8-5df0-547f-b3c1-a5482ce5859f/scratchpad/data/${low}_1m.csv; grep -E "$pat" /tmp/claude-0/-home-user-opogabuuga/586832a8-5df0-547f-b3c1-a5482ce5859f/scratchpad/data/${low}_1m.csv) > /tmp/claude-0/-home-user-opogabuuga/586832a8-5df0-547f-b3c1-a5482ce5859f/scratchpad/agents/engine/${low}_$tag.csv
  nice -n 10 env PYTHONPATH=. $P ../docs/results/tools/research.py $sym /tmp/claude-0/-home-user-opogabuuga/586832a8-5df0-547f-b3c1-a5482ce5859f/scratchpad/agents/engine/${low}_$tag.csv /tmp/claude-0/-home-user-opogabuuga/586832a8-5df0-547f-b3c1-a5482ce5859f/scratchpad/agents/engine/plan_all.yaml /tmp/claude-0/-home-user-opogabuuga/586832a8-5df0-547f-b3c1-a5482ce5859f/scratchpad/agents/engine/${low}_$tag.json 2>&1 | grep -v info
  if [ $sym = MNQ ]; then a="0.25 0.50 1.00"; else a="0.10 1.00 1.60"; fi
  DUMP_ROWS=/tmp/claude-0/-home-user-opogabuuga/586832a8-5df0-547f-b3c1-a5482ce5859f/scratchpad/agents/engine/rows_${low}_$tag.json nice -n 10 $P ../docs/results/tools/indscreen.py /tmp/claude-0/-home-user-opogabuuga/586832a8-5df0-547f-b3c1-a5482ce5859f/scratchpad/agents/engine/${low}_$tag.json /tmp/claude-0/-home-user-opogabuuga/586832a8-5df0-547f-b3c1-a5482ce5859f/scratchpad/agents/engine/${low}_$tag.csv $a 1.75 > /tmp/claude-0/-home-user-opogabuuga/586832a8-5df0-547f-b3c1-a5482ce5859f/scratchpad/agents/engine/ind_${low}_$tag.txt 2>&1
  echo DONE $sym $tag
done
