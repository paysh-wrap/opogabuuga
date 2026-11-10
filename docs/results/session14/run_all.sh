#!/bin/bash
# usage: run_all.sh causal|hindsight   (runs the D70/D71/D73/D74 engines on the chosen fade rule; outputs in session14/out/<rule>)
R=$1
D=$(cd "$(dirname "$0")/.." && pwd)
T=$D/session14/out/$R
mkdir -p "$T"
export STUDY_OUT=$T PYTHONPATH=$D/../../backend FADE_RULE=$R
cd "$D/session10/five_year" && python3 kill_study.py run > "$T/kill_run.log" 2>&1
cd "$D/session10/five_year" && python3 kill_study.py fadecode > "$T/kill_fadecode.log" 2>&1
cd "$D/session11" && python3 pm_fade_d57_study.py run > "$T/pmfade_run.log" 2>&1
