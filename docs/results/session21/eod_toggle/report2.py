import json,sys,os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from sim import load_plans
N=json.load(open('results.json')); O=json.load(open('results_noshrink.json')); P=load_plans(); r0=lambda x:int(round(x))
def brake(row): return None if row.get('brake_below') is None else f"{row['brake_contracts']} below {int(row['brake_below']*100)}% cushion"
def f(c): return '{pass: %d, bust: %d, stuck: %d, open: %d, days: %d}'%tuple(r0(c[k]) for k in('pass','bust','stuck','open','days'))
y=['version: 1','study: "Session 21 realistic account sim: NOISE shipped eval config, kill switch $50, pre-trade room check, brake rows, incl. D57 stop shrink, 2021-10..2026-10 (regular_fade_on rows: without D57 shrink, 2019-05..2026-11 stream)"','source: docs/results/session21/eod_toggle/RESULTS.md','plans:']
for p in P:
    y.append(f'  {p}:')
    for tab,tt,src,fade in(('regular','regular',N,0),('suggested','suggested',N,0),('high','high',N,0),('regular_fade_on','regular',O,1)):
        row=P[p]['tabs'][tt]; b=brake(row)
        y+= [f'    {tab}:',f'      contracts: {row["contracts"]}',f'      brake: {json.dumps(b) if b else "null"}']
        for m in('on','off'):
            g=lambda e: src[f'{p}|{tt}|{e}|{m}|fade'] if fade else src[f'{p}|{tt}|{e}|{m}'] if not fade and src is N else src[f'{p}|{tt}|{e}|{m}|base']
            y.append(f'      eod_{m}: {{'+', '.join(f'{e}: {f(g(e))}' for e in('all','is','j'))+'}')
open('eval_odds.yaml','w').write('\n'.join(y)+'\n')
def t(title,fn):
    L=[f'\n**{title}**\n']
    for m in('off','on'):
        L.append(f'\nEOD toggle {m.upper()} (pass / bust %; bust incl. stuck; stuck in brackets)\n\n| plan | c | ALL | IS | J |\n|---|---|---|---|---|')
        for p in P:
            c=[fn(p,e,m) for e in('all','is','j')]
            L.append(f'| {p} | {P[p]["tabs"]["regular"]["contracts"]} | '+' | '.join(f'{r0(x["pass"])} / {r0(x["bust"])} ({r0(x["stuck"])})' for x in c)+' |')
    return '\n'.join(L)
S=N['sanity']; so=O['sanity']
def tabs(tt): return t(f'{tt} table (with D57 shrink)',lambda p,e,m:N[f'{p}|{tt}|{e}|{m}'])
head="""The two app rules plus the D57 stop shrink: see Pro rows. With the shrink the account no longer gets stuck early (the app tightens the stop instead of skipping), so the realistic numbers sit close to the old closed-trade study; EOD toggle ON vs OFF differences are listed in the tables below (OFF = kill on open P&L)."""
old=open('RESULTS_noshrink.md').read().split('## Tables',1)
md=f"""# Session 21 - EOD toggle: realistic account simulator (incl. D57 stop shrink)

Scripts: `sim2.py`, `run2.py`, `report2.py` (new, with shrink); `sim.py`, `run.py`, `report.py` (previous, no shrink). Raw `results.json` (new), `results_noshrink.json`.
Stream: session 20 `streams_BASE.csv` (2021-10-22..2026-10-30, 654 tr), entry price = MNQ open[ek] from days12.pkl. Eras ALL 2021-10-21..2026-10-30, IS ..2025-11-05, J 2025-11-06..2026-10-30. Bootstrap = session-20 protocol (`lib.eval_boot`: 10-day blocks, uniform start, 600 paths x 400 sessions, seed 7). Kill distance/margin per plan YAML.
D57 shrink: allowed = 0.6 x room0; if q x risk > allowed, stop shrinks to per_ticks (min 0.2 % of entry, else skip); trade loses S' if mae >= S' else original pnl; then worst-case check and the mode's kill rule.

## Headline
SEE_HEAD

## Sanity (mode ON, room/kill/shrink off): Pro 25K IS {r0(S['lucid_pro_25k|is']['pass'])}/{r0(S['lucid_pro_25k|is']['bust'])} (session 20: 72/28), J {r0(S['lucid_pro_25k|j']['pass'])}/{r0(S['lucid_pro_25k|j']['bust'])} (68/32): exact match.
(Note: my first-run block sampler differed from session 20's and gave 79/21 on IS; adopted session 20's.)

## Tables (with D57 shrink)
{tabs('regular')}
{tabs('suggested')}
{tabs('high')}

## Fade-on rows: not rebuilt with shrink
Kept from the previous run, labelled WITHOUT D57 shrink (2019-05..2026-11 stream); see the section below. In eval_odds.yaml `regular_fade_on` carries those values.

## Caveats
Closed-trade DLL model; MAE is per trade (touch time approximate); news not modelled; J small (118 trades, +-5 pt). STUCK = shrunk stop under 0.2 % of price for every later trade (or balance within kill distance of floor).

# Without D57 shrink (previous run, 2019-05..2026-11 stream)
{old[1] if len(old)>1 else ''}"""
open('RESULTS.md','w').write(md)
