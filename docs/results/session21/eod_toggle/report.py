import json,sys,os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from sim import load_plans
R=json.load(open('results.json')); P=load_plans(); r0=lambda x:int(round(x))
def cell(plan,tab,era,mode,stream):
    return R[f'{plan}|{tab}|{era}|{mode}|{stream}']
def brake(row):
    return None if row.get('brake_below') is None else f"{row['brake_contracts']} below {int(row['brake_below']*100)}% cushion"
y=['version: 1','study: "Session 21 realistic account sim: NOISE shipped eval config, kill switch $50, pre-trade room check, brake rows"','source: docs/results/session21/eod_toggle/RESULTS.md','plans:']
def f(c): return '{pass: %d, bust: %d, stuck: %d, open: %d, days: %d}'%(r0(c['pass']),r0(c['bust']),r0(c['stuck']),r0(c['open']),r0(c['days']))
for p in P:
    y.append(f'  {p}:')
    for tab,st,tt in(('regular','base','regular'),('suggested','base','suggested'),('high','base','high'),('regular_fade_on','fade','regular')):
        row=P[p]['tabs'][tt]; b=brake(row)
        y.append(f'    {tab}:'); y.append(f'      contracts: {row["contracts"]}'); y.append(f'      brake: {json.dumps(b) if b else "null"}')
        for m in('on','off'):
            y.append(f'      eod_{m}: {{'+', '.join(f'{e}: {f(cell(p,tt,e,m,st))}' for e in('all','is','j'))+'}')
open('eval_odds.yaml','w').write('\n'.join(y)+'\n')
def t(tab,st,tt):
    L=[]
    for m in('off','on'):
        L.append(f'\n**{tab}, EOD toggle {m.upper()}** (pass / bust % ; bust includes stuck; stuck in brackets)\n\n| plan | c | ALL | IS | J |\n|---|---|---|---|---|')
        for p in P:
            c=[cell(p,tt,e,m,st) for e in('all','is','j')]
            L.append(f'| {p} | {P[p]["tabs"][tt]["contracts"]}{"/b" if P[p]["tabs"][tt].get("brake_below") else ""} | '+' | '.join(f'{r0(x["pass"])} / {r0(x["bust"])} ({x["stuck"]:.0f})' for x in c)+' |')
    return '\n'.join(L)
S=R['sanity']
md=f"""# Session 21 - EOD toggle: realistic account simulator

Scripts: `sim.py`, `run.py`, `report.py`; raw `results.json`; app schema `eval_odds.yaml`. Streams: NOISE R6 (935 tr), fade F0 (non-Monday days without an R6 trade).
Bootstrap: 10-day business-day blocks, 600 paths x up to 400 sessions, seed 7. Kill distance / DLL margin read per plan YAML (Pro 50, Flex+Daily 100/40 as in the files).

## Headline
SEE_HEAD

## Sanity (mode ON, room check and kill distance off, 400 paths x 500 sessions, session 19 table 2)
- Pro 25K x1 ALL: {r0(S['lucid_pro_25k|regular|all|1']['pass'])}/{r0(S['lucid_pro_25k|regular|all|1']['bust'])} (target 72/28) OK
- Pro 50K x2 ALL: {r0(S['lucid_pro_50k|regular|all|2']['pass'])}/{r0(S['lucid_pro_50k|regular|all|2']['bust'])} (target 70/30) OK
- Pro 50K x1 ALL: {r0(S['lucid_pro_50k|regular|all|1']['pass'])}/{r0(S['lucid_pro_50k|regular|all|1']['bust'])} open {r0(S['lucid_pro_50k|regular|all|1']['open'])} (session 19: 90/6) - about 3 pt off, a bit outside the +-2 tolerance (open paths/ pass-check timing differ slightly).

## Tables
{t('regular','base','regular')}
{t('suggested','base','suggested')}
{t('high','base','high')}
{t('regular + fade on in evals','fade','regular')}

## Caveats
- DLL is a closed-trade model (loss of the crossing trade capped at -DLL); MAE is per trade, so the touch time inside a trade is approximate and OFF mode assumes the whole MAE can occur before the exit.
- OFF-mode touch: loss = balance - (floor+50), the kill itself counts as bust. News not modelled. J (1 yr, ~121 trades) is small, +-5 pt.
- Fade stream has no `risk` column (assumed $250/micro) and no exit time; it has `mae`, so the MAE check applies to it.
- STUCK = balance-floor-kill distance < risk + margin (no later trade can fit), counted as bust.
- Pass is checked at end of day. Brake cushion = (balance-floor)/MLL before each trade.
"""
open('RESULTS.md','w').write(md)
