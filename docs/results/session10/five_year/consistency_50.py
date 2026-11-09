import sys, statistics as st, random
sys.path.insert(0,'/home/user/opogabuuga/backend')
from decimal import Decimal as D
from pathlib import Path
from app.config import load_rules
from app.backtest.income_projection import research_days, rules_view, eval_view, eval_path, size_for, ZERO, CENT
RD=Path('/home/user/opogabuuga/config/rules')
_,DAYS=research_days(); DAYS=list(DAYS)
SIZES={'25k':(1,None),'50k':(2,(D('0.5'),1)),'100k':(2,(D('0.3'),1)),'150k':(3,(D('0.5'),2))}
def rules(kind,s): return load_rules(RD/f'lucid_{kind}_{s}.yaml').rules

def fpath(days,r,qty,brake,cons,min_gap=2,pct_cap=None,stop=None,stop_floor=ZERO):
    """cons: consistency % or None. stop: day-stop share (e.g. .35). Returns dict."""
    bal=peak=r.start; floor=r.start-r.mll; cycle=[]; paid=ZERO; pays=[]
    last=-99; checks=elig=consfail=0; blocked_cycles=0; cyc_blocked=False; cyc_first_block=None; waits=[]; cycles=0
    status='OPEN'; N=len(days)
    for n,trades in enumerate(days):
        day=ZERO; q=qty
        if brake and bal-floor<brake[0]*r.mll: q=min(q,brake[1])
        for p in trades:
            if stop is not None and day>0:
                if day>=stop*max(sum(cycle,ZERO)+day,stop_floor): break
            p*=q
            if r.dll is not None and day+p<=-r.dll: p=-r.dll-day
            bal+=p; day+=p
            if bal<=floor: return dict(paid=paid,pays=pays,status='BUST',checks=checks,elig=elig,consfail=consfail,bc=blocked_cycles,cycles=cycles,waits=waits,n=n+1)
            if r.dll is not None and day<=-r.dll: break
        if trades: cycle.append(day)
        peak=max(peak,bal)
        floor=r.lock_level if peak>=r.lock_trigger else max(floor,peak-r.mll)
        if len(pays)>=r.max_payouts: break
        if n+1-last>=min_gap:
            cp=sum(cycle,ZERO)
            if cp>=r.min_cycle_profit and balance_ok(bal,r):
                checks+=1
                cok = cons is None or max(cycle)<=D(cons)/100*cp
                if not cok:
                    consfail+=1
                    if not cyc_blocked: cyc_blocked=True; cyc_first_block=n
                else:
                    cap=r.max_first if not pays else r.max_next
                    amt=min(bal-r.buffer,cap)
                    if pct_cap is None or bal-r.buffer>=pct_cap*cap:
                        if r.min_profitable_days==0 or sum(1 for x in cycle if x>=r.min_day_profit)>=r.min_profitable_days:
                            elig+=1
                            bal-=amt; paid+=(amt*r.split).quantize(CENT); pays.append((n+1,amt)); last=n+1; cycles+=1
                            if cyc_blocked: blocked_cycles+=1; waits.append(n-cyc_first_block)
                            cyc_blocked=False; cyc_first_block=None; cycle=[]
                            if r.lock_mll_on_payout: floor=max(floor,r.lock_level)
    return dict(paid=paid,pays=pays,status='MAX' if len(pays)>=r.max_payouts else 'OPEN',checks=checks,elig=elig,consfail=consfail,bc=blocked_cycles,cycles=cycles,waits=waits,n=N)
def balance_ok(bal,r): return bal-r.buffer>=r.min_request

def proj(s,cons,pct_cap=None,stop=None,stop_floor=ZERO,H=260,acc=5):
    r=rules_view(rules('pro',s)); q,b=SIZES[s]
    out=[fpath(DAYS[i:i+H],r,q,b,cons,2,pct_cap,stop,stop_floor) for i in range(0,len(DAYS)-H,2)]
    paid=[o['paid']*acc for o in out]; n=len(out)
    firsts=[o['pays'][0][0] for o in out if o['pays']]
    npay=sum(len(o['pays']) for o in out)/n
    ch=sum(o['checks'] for o in out); cf=sum(o['consfail'] for o in out)
    cyc=sum(o['cycles'] for o in out); bc=sum(o['bc'] for o in out); w=[x for o in out for x in o['waits']]
    return dict(n=n,pay_acct_yr=npay,per2w=float(sum(paid)/n)/26,mean=float(sum(paid)/n),med=float(st.median(paid)),
      any=100*sum(1 for o in out if o['pays'])/n,first=st.median(firsts) if firsts else None,
      bust=100*sum(1 for o in out if o['status']=='BUST')/n,consfail=100*cf/ch if ch else 0,
      blockedcyc=100*bc/cyc if cyc else 0,waitmed=st.median(w) if w else 0,waitmean=st.mean(w) if w else 0)
def fmt(d): return f"{d['pay_acct_yr']:.2f} | {d['per2w']:.0f} | {d['mean']:.0f} / {d['med']:.0f} | {d['any']:.0f}% | {d['first']} | {d['bust']:.1f}% | {d['consfail']:.0f}% | {d['blockedcyc']:.0f}% | {d['waitmed']:.0f}/{d['waitmean']:.1f}"
HDR="| plan | cons | pay/acct/yr | 5-acct $/2wk | year mean / median | >=1 payout | med sess to 1st | bust | checks failing only on consistency | cycles blocked by big day | wait med/mean sess |\n|---|---|---|---|---|---|---|---|---|---|---|"
out=[]
def P(*a): 
    s=' '.join(str(x) for x in a); print(s); out.append(s)
P("# Consistency 50% vs 40% study (MNQ MAIN strategy trades, 2021-11..2026-10, rolling starts every 2 sessions, 260-session horizon, 5 accounts)\n")
P("## Part 1a. Pro funded, as-soon-as-eligible (check every session, >=2 sessions after prior payout)\n"); P(HDR)
for s in SIZES:
    for c in (40,50): P(f"| {s} | {c or 'none'} | "+fmt(proj(s,c)))
P("\n## Part 1b. Pro funded, wait for payout >= 50% of cap\n"); P(HDR)
for s in SIZES:
    for c in (40,50): P(f"| {s} | {c or 'none'} | "+fmt(proj(s,c,pct_cap=D('0.5'))))
# Part 2
P("\n## Part 2a. Daily P&L distribution at 1 micro (days with trades)")
dp=[sum(t,ZERO) for t in DAYS if t]; fl=sorted(float(x) for x in dp)
q=lambda p: fl[int(p*(len(fl)-1))]
P(f"n days {len(fl)} (of {len(DAYS)} sessions); mean {st.mean(fl):.1f}; median {st.median(fl):.1f}; p5 {q(.05):.0f} p25 {q(.25):.0f} p75 {q(.75):.0f} p95 {q(.95):.0f} p99 {q(.99):.0f}; max {fl[-1]:.0f} min {fl[0]:.0f}; win days {100*sum(1 for x in fl if x>0)/len(fl):.0f}%")
P("\n## Part 2b. Share of rolling windows (of N trading days, profit>0) whose best day exceeds X% of window profit\n| window | profitable windows | >30% | >40% | >50% | median best-day share |\n|---|---|---|---|---|---|")
for w in (3,5,10):
    sh=[]
    for i in range(len(fl:=[float(x) for x in dp])-w+1):
        win=fl[i:i+w]; tot=sum(win)
        if tot>0: sh.append(max(win)/tot)
    P(f"| {w} | {len(sh)} | {100*sum(x>.3 for x in sh)/len(sh):.0f}% | {100*sum(x>.4 for x in sh)/len(sh):.0f}% | {100*sum(x>.5 for x in sh)/len(sh):.0f}% | {st.median(sh):.2f} |")
P("\n## Part 2c. Consistency day-stop (stop for the day once today's realized profit >= X% of cycle-so-far+today; floor = denominator min). as-soon policy\n| plan | cons | day-stop | floor | 5-acct $/2wk | mean yr | median yr | pay/acct/yr | bust | cons-fail checks | 1st payout med |\n|---|---|---|---|---|---|---|---|---|---|---|")
for s in SIZES:
    r=rules_view(rules('pro',s))
    for c,sp in ((40,.35),(50,.45)):
        for lab,stop,fl_ in (('none',None,ZERO),('literal',D(str(sp)),ZERO),('floor=min cycle x2',D(str(sp)),r.min_cycle_profit*2),('floor=1st cap',D(str(sp)),r.max_first)):
            d=proj(s,c,stop=stop,stop_floor=fl_)
            P(f"| {s} | {c} | {'-' if stop is None else sp} {lab} | {fl_} | {d['per2w']:.0f} | {d['mean']:.0f} | {d['med']:.0f} | {d['pay_acct_yr']:.2f} | {d['bust']:.1f}% | {d['consfail']:.0f}% | {d['first']} |")
# Part 3
P("\n## Part 3. Flex eval (3 profitable days, DLL none), target per plan\n| plan | cons | starts | PASS | BUST | OPEN | median days to pass | mean days |\n|---|---|---|---|---|---|---|---|")
HZ={'25k':120,'50k':120,'100k':250,'150k':250}
for s in SIZES:
    r=rules('flex',s); ev=eval_view(r); q,b=SIZES[s]; H=HZ[s]
    for c in (40,50):
        from dataclasses import replace
        e2=replace(ev,consistency_pct=None if c is None else D(c))
        res=[eval_path(DAYS[i:i+H],e2,q,None,5,H,b) for i in range(0,len(DAYS)-H,2)]
        n=len(res); pd=[d for k,d in res if k=='PASS']
        P(f"| {s} | {c or 'none'} | {n} | {100*len(pd)/n:.0f}% | {100*sum(k=='BUST' for k,_ in res)/n:.0f}% | {100*sum(k=='OPEN' for k,_ in res)/n:.0f}% | {st.median(pd) if pd else '-'} | {st.mean(pd) if pd else 0:.0f} |")
Path('results.md').write_text('\n'.join(out))
