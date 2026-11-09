import sys, json
sys.path.insert(0, "/home/user/opogabuuga/backend")
from decimal import Decimal as D
from pathlib import Path
from statistics import median, mean
from app.config import load_rules
from app.backtest.income_projection import rules_view, research_days, size_for, ZERO, CENT

names, DAYS = research_days()
DAYS = list(DAYS); HOR = 260; STEP = 2; ACC = 5
starts = list(range(0, max(1, len(DAYS) - HOR), STEP))
half1 = [names[i] < "2024-01-01" for i in starts]

def elig(r, bal, cycle, n_paid):
    """returns (amount, reason)"""
    cp = sum(cycle, ZERO)
    if cp < r.min_cycle_profit or cp <= 0: return ZERO, "cycle_profit"
    if r.consistency_pct is not None and max(cycle) > r.consistency_pct/100*cp: return ZERO, "consistency"
    amt = balance_amt = bal - r.buffer
    cap = r.max_first if n_paid == 0 else r.max_next
    if cap is not None: amt = min(amt, cap)
    if amt < r.min_request: return ZERO, "min_amount_buffer"
    return amt.quantize(CENT), "ok"

# policy(r, n1, last_n, n_paid, amt, cap) -> want request (checked only when eligible OR for fixed cadence)
def fixed(k): return ("fixed%d"%k, lambda r,n1,last,np_,amt,cap: (n1 % k == 0), True)
def asap(): return ("asap", lambda r,n1,last,np_,amt,cap: True, False)
POL = [fixed(1), fixed(2), fixed(3), fixed(5), fixed(10), asap(),
  ("asap_fullcap", lambda r,n1,last,np_,amt,cap: cap is None or amt >= cap, False),
  ("asap_>=1000", lambda r,n1,last,np_,amt,cap: amt >= 1000, False),
  ("asap_>=50%cap", lambda r,n1,last,np_,amt,cap: cap is None or amt >= cap/2, False),
  ("gap2 (every 2-3)", lambda r,n1,last,np_,amt,cap: n1-last >= 2, False),
  ("gap3", lambda r,n1,last,np_,amt,cap: n1-last >= 3, False)]

def path(days, r, base, brake, pol):
    name, want, is_fixed = pol
    bal = peak = r.start; floor = r.start - r.mll; cycle=[]; paid=ZERO; pays=0; last=0
    att=0; fails={"cycle_profit":0,"consistency":0,"min_amount_buffer":0}
    status="OPEN"
    for n, trades in enumerate(days):
        day = ZERO; qty = base
        if brake and bal-floor < brake[0]*r.mll: qty = min(qty, brake[1])
        for p in trades:
            p *= qty
            if r.dll is not None and day+p <= -r.dll: p = -r.dll-day
            bal += p; day += p
            if bal <= floor: return paid, pays, "BUST", att, fails
            if r.dll is not None and day <= -r.dll: break
        if trades: cycle.append(day)
        peak = max(peak, bal)
        floor = r.lock_level if peak >= r.lock_trigger else max(floor, peak-r.mll)
        if pays < (r.max_payouts or 99):
            n1=n+1
            cap = r.max_first if pays==0 else r.max_next
            amt, why = elig(r, bal, cycle, pays)
            if is_fixed:
                req = want(r,n1,last,pays,amt,cap)
                if req:
                    att+=1
                    if amt==0: fails[why]+=1
            else:  # check-every-day policies: request only when eligible and rule satisfied
                req = amt>0 and want(r,n1,last,pays,amt,cap)
                if req: att+=1
            if req and amt>0:
                bal -= amt; paid += (amt*r.split).quantize(CENT); pays+=1; last=n1; cycle=[]
                if r.lock_mll_on_payout: floor=max(floor,r.lock_level)
        if r.max_payouts is not None and pays >= r.max_payouts: return paid,pays,"MAX_PAYOUTS",att,fails
    return paid,pays,"OPEN",att,fails

def q(xs,p): s=sorted(xs); return s[min(len(s)-1,int(p*(len(s)-1)+.5))]

PLANS = [("25K R1",25,1,None),("50K R2",50,2,(D("0.5"),1)),("100K R2",100,2,(D("0.3"),1)),
         ("150K Reg3",150,3,(D("0.5"),2)),("150K High4",150,4,(D("0.5"),2))]
out={}
for pname,sz,base,brake in PLANS:
    r = rules_view(load_rules(Path(f"/home/user/opogabuuga/config/rules/lucid_pro_{sz}k.yaml")).rules)
    out[pname]={}
    for pol in POL:
        res=[path(DAYS[i:i+HOR], r, base, brake, pol) for i in starts]
        paid=[float(x[0])*ACC for x in res]
        bust=[x[2]=="BUST" for x in res]
        def b(mask): 
            v=[bu for bu,m in zip(bust,half1) if m==mask]; return 100*sum(v)/len(v)
        def h(mask,f): 
            v=[f(x) for x,m in zip(res,half1) if m==mask]; return sum(v)/len(v)
        att=sum(x[3] for x in res); fl={k:sum(x[4][k] for x in res) for k in res[0][4]}
        out[pname][pol[0]]=dict(per2w=mean(paid)/26, mean=mean(paid), med=median(paid), p25=q(paid,.25),
          npay=mean(x[1] for x in res), bust=100*sum(bust)/len(bust), any=100*sum(x[1]>0 for x in res)/len(res),
          bust_h1=b(True), bust_h2=b(False), mean_h1=h(True,lambda x:float(x[0])*ACC), mean_h2=h(False,lambda x:float(x[0])*ACC),
          med_h1=median([p for p,m in zip(paid,half1) if m]), med_h2=median([p for p,m in zip(paid,half1) if not m]),
          surv=100*sum(x[2]!="BUST" for x in res)/len(res), att=att/len(res), fail=fl, fail_pct=(100*sum(fl.values())/att if att else 0),
          cons_pct=(100*fl["consistency"]/att if att else 0))
json.dump(out,open("results.json","w"),indent=1)
# report
L=["# Payout-request policy study (agentI)\n","5 accounts, starts every 2 sessions (%d starts), 260-session horizon, MAIN strategy research days, size+brake per D64. Take-home = cash paid (after 90%% split) only.\n"%len(starts)]
for pname in out:
    base=out[pname]["fixed10"]
    L.append(f"\n## {pname}\n\n| policy | per-2wk | mean yr | median | p25 | payouts/acct/yr | bust% | >=1 pay% | bust H1/H2 | mean H1/H2 | median H1/H2 | req fail% (consist.) |\n|---|---|---|---|---|---|---|---|---|---|---|---|")
    ok=[]
    for k,v in out[pname].items():
        okb = v["bust_h1"]<=base["bust_h1"]+2 and v["bust_h2"]<=base["bust_h2"]+2
        if okb: ok.append(k)
        L.append(f"| {k}{'' if okb else ' (bust+)'} | {v['per2w']:.0f} | {v['mean']:.0f} | {v['med']:.0f} | {v['p25']:.0f} | {v['npay']:.2f} | {v['bust']:.1f} | {v['any']:.0f} | {v['bust_h1']:.1f}/{v['bust_h2']:.1f} | {v['mean_h1']:.0f}/{v['mean_h2']:.0f} | {v['med_h1']:.0f}/{v['med_h2']:.0f} | {v['fail_pct']:.0f} ({v['cons_pct']:.0f}) |")
    w=max(ok,key=lambda k:(out[pname][k]["mean"]))
    wm=max(ok,key=lambda k:(out[pname][k]["med"]))
    L.append(f"\nWinner by mean: **{w}**; by median: **{wm}**. gap2 vs best mean: {100*(out[pname]['gap2 (every 2-3)']['mean']/out[pname][w]['mean']-1):.1f}%, vs best median: {100*(out[pname]['gap2 (every 2-3)']['med']/out[pname][wm]['med']-1):.1f}%")
Path("report.md").write_text("\n".join(L))
print("\n".join(L))
