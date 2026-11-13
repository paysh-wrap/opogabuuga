import json,sys,os,yaml; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from sim import load_plans
N=json.load(open('results.json')); P=load_plans(); r0=lambda x:int(round(x))
M35=json.load(open('results_35.json'))
OLD=yaml.safe_load(open('../eod_toggle/eval_odds.yaml'))['plans']
def brake(row): return None if row.get('brake_below') is None else f"{row['brake_contracts']} below {int(row['brake_below']*100)}% cushion"
def f(c): return '{pass: %d, bust: %d, stuck: %d, open: %d, days: %d}'%tuple(r0(c[k]) for k in('pass','bust','stuck','open','days'))
y=['version: 1','study: "Session 21 realistic account sim with new Lucid rules: Pro eval consistency 40 %, Pro 25K DLL 600, LucidScale 60 %, consistency day stop 38 %, D57 shrink, 2021-10..2026-10 (regular_fade_on rows also with D57 shrink, same stream window)"','source: docs/results/session21/pro_rules/RESULTS.md','plans:']
for p in P:
    y.append(f'  {p}:')
    for tab,tt,fade in(('regular','regular',0),('suggested','suggested',0),('high','high',0),('regular_fade_on','regular',1)):
        row=P[p]['tabs'][tt]; b=brake(row)
        y+=[f'    {tab}:',f'      contracts: {row["contracts"]}',f'      brake: {json.dumps(b) if b else "null"}']
        for m in('on','off'):
            y.append(f'      eod_{m}: {{'+', '.join(f'{e}: {f(N[f"{p}|{tt}|{e}|{m}|{fade}"])}' for e in('all','is','j'))+'}')
open('eval_odds.yaml','w').write('\n'.join(y)+'\n')
def cell(x): return f'{r0(x["pass"])} / {r0(x["bust"])} / {r0(x["open"])} ({r0(x["days"])}d)'
def oc(x): return f'{x["pass"]} / {x["bust"]} / {x["open"]} ({x["days"]}d)'
H=['| plan | c | ALL before | ALL 35 % | ALL 38 % | J before | J 35 % | J 38 % |','|---|---|---|---|---|---|---|---|']
for p in P:
    o=OLD[p]['regular']['eod_off']; n=lambda e:N[f'{p}|regular|{e}|off|0']
    H.append(f'| {p} | {P[p]["tabs"]["regular"]["contracts"]} | {oc(o["all"])} | {cell(M35[f"{p}|regular|all|off|0"])} | {cell(n("all"))} | {oc(o["j"])} | {cell(M35[f"{p}|regular|j|off|0"])} | {cell(n("j"))} |')
def t(title,tt,fade):
    L=[f'\n**{title}** (pass / bust / open %, median days to pass; bust incl. stuck)\n']
    for m in('off','on'):
        L.append(f'\nEOD toggle {m.upper()}\n\n| plan | c | ALL | IS | J |\n|---|---|---|---|---|')
        for p in P: L.append(f'| {p} | {P[p]["tabs"][tt]["contracts"]} | '+' | '.join(cell(N[f'{p}|{tt}|{e}|{m}|{fade}']) for e in('all','is','j'))+' |')
    return '\n'.join(L)
md=f"""# Session 21 - Pro rules (new Lucid rules) realistic account simulator

Scripts: `sim.py` (plans), `sim2.py` (sim), `run2.py`, `report2.py`; raw `results.json`, output `eval_odds.yaml`. Copied from `../eod_toggle/`.
Stream/eras/bootstrap/kill/room check/brake/D57 shrink (0.6, min stop 0.2 %, STUCK when 0.6 x room < $112): unchanged from eod_toggle.

## Changes vs eod_toggle
1. Pro EVAL consistency 40 % (best day <= 40 % of profit at pass check); min profitable days unchanged (1).
2. Pro 25K DLL 600 (50K 1200 / 100K 1800 / 150K 2700). Pro values read from the final YAMLs (asserted in `sim.py`).
3. LucidScale (Pro): once the MLL has locked, DLL = 60 % x (peak EOD balance - start balance), peak keeps rising.
4. App consistency day stop for every plan with an EVAL consistency % (Pro, Flex, Daily): day_stop = (cons - buffer 2 = 38 %) x target ($475 on 25K, 1,140 on 50K, 2,280 on 100K, 3,420 on 150K; buffer from the YAMLs, was 5 = 35 % in the previous run); a trade that would push today above it is capped to today = day_stop and no more trades that day. (40 % entry cap not applied.)
5. Fade-on rows rebuilt with D57 shrink: session-19 `streams_fade_F0.csv` limited to 2021-10-21..2026-10-30 ({0} fade trades after removing Mondays and NOISE days), entry = MNQ open[ek], risk $250/micro.

## Headline: regular table, EOD toggle OFF, session-21 eod_toggle (before) -> 35 % day stop (previous run, results_35.json; note: that run's day-stop was 35 %) -> 38 % day stop (this run); pass / bust / open % (median days to pass)

""".replace('{0}','389')+'\n'.join(H)+"\n"+t('regular','regular',0)+t('suggested','suggested',0)+t('high','high',0)+t('regular + fade on (D57 shrink)','regular',1)+"""

## What changed most and why
- (Numbers in this list are from the 35 % run; see the headline table for 38 %.) Pro 25K: ALL 60/40 -> 56/44, J 40/60 -> 38/62, median days 48 -> 58 (ALL). Pro 50K: J 57/43 -> 52/48. Pro 100K/150K barely move (1-5 pts, days +6): their day-stop level ($2,100 / $3,150) and the 40 % cap almost never bind at 2-3 micros.
- Consistency day stop (all plans with an eval consistency %): caps a winning day at $475 on 25K (1,140 on 50K; previously 437.50 / 1,050). Biggest effect on 25K/50K where one NOISE winner (max $1,672 per micro) is a large part of the $1,250/$2,500 target: wins are truncated, so passes take longer and the bootstrap path gets fewer big days. Flex/Daily 25K lose 3-4 pts pass (53 -> 50 ALL, 34 -> 30 J) and Flex 50K 62 -> 60 (J 49 -> 47). It also removes the consistency-fail path at the pass check (best day <= 38 % target <= 40 % of profit once the target is reached).
- Pro eval consistency 40 %: after the day stop it is nearly never binding; it mainly forces more profitable days.
- Pro 25K DLL 600 (was none): closed-trade DLL, 1 micro, rarely binds (stops are <= $250) so small effect.
- LucidScale: only after the MLL lock (peak EOD >= lock trigger); only matters if a later day loses more than 60 % of peak profit; negligible before the pass.
- Fade-on rows rebuilt with D57 shrink (389 fade trades, non-Monday days without NOISE).
- A first run of this study produced garbage (flex 150K 78 -> 16 pass) because another agent was mid-edit on config/rules (plans read at run time); rerun with unchanged Flex/Daily YAMLs gave the numbers here. YAML md5s used: `yaml_md5.txt`.

## Caveats
Closed-trade DLL/day-stop model (running-trade intraday touch not modelled; capped pnl is an approximation); MAE per trade; news not modelled; J era small (118 trades, about +-5 pts); fade stream uses an assumed $250 risk per micro; LucidScale only simulated in the EVAL window (funded not simulated).
"""
open('RESULTS.md','w').write(md)
