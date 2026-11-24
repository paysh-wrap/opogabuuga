import sys, json, copy; sys.path.insert(0,'/home/user/paytience/docs/results/agent_review_2026-11-24/held_out_tests')
import numpy as np, pandas as pd, hot_lib as H
from hot_lib import stats, win
R={}; NS=60
base=H.gen2(); R['base']={w:stats(base,w) for w in('pick','judge','all')}
assert len(base)==654 and round(base.pnl.sum())==19293
def ctl(kw):
    nets=[];pfs=[]
    for s in range(NS):
        t=win(H.gen2(rnd=s,**kw),'judge'); p=t.pnl.values; nets.append(p.sum()); pfs.append(p[p>0].sum()/-p[p<0].sum())
    return float(np.percentile(nets,95)),float(np.percentile(pfs,95))
def run(name,variants):
    rows={}
    for k,kw in variants.items():
        t=H.gen2(**kw); rows[k]=dict(kw=str(kw),pick=stats(t,'pick'),judge=stats(t,'judge'))
    bp=R['base']['pick']
    ok=[k for k,r in rows.items() if r['pick']['net']>=bp['net'] and r['pick']['pf']>=bp['pf'] and k!='shipped']
    pickk=max(ok,key=lambda k:rows[k]['pick']['net']) if ok else None
    res=dict(rows=rows,picked=pickk)
    if pickk:
        j=rows[pickk]['judge']; b=R['base']['judge']; c=ctl(variants[pickk])
        res['control_p95_net_pf']=c
        res['pass']=bool(j['net']>b['net'] and j['pf']>b['pf'] and j['n']>=60 and j['net']>c[0] and j['pf']>c[1])
    R[name]=res
# idea1: trigger 60..140 step 20 x offset {0,10,20,30}
v1={f"L{a}/{o}":dict(lock=(float(a),float(o))) for a in (60,80,100,120,140) for o in (0,10,20,30) if not(a==100 and o==10)}
run('idea1',v1)
v3={f"S{s}":dict(stop_usd=float(s)) for s in (150,200,250,300)}
run('idea3',v3)
# idea6 early closes
D=H.D; short={}
for d,a in D:
    if d<H.PICK0: continue
    v=np.where(~np.isnan(a['close']))[0]
    if len(v)<390 : short[d]=int(v[-1]) if len(v) else -1
R['early_days']=short
# padded run
orig=list(H.D); newD=[]
for d,a in orig:
    if d in short and short[d]>0:
        b={k:x.copy() for k,x in a.items()}; L=short[d]
        for k in ('open','high','low','close','vwap'):
            b[k][L+1:]=b['close'][L]
        newD.append((d,b))
    else: newD.append((d,a))
asis=H.gen2(); H.D[:]=newD; pad=H.gen2(); H.D[:]=orig
sd=set(short)
def sub(t): return t[t.d.isin(sd)]
R['idea6']=dict(n_days=len(short),asis_trades=len(sub(asis)),asis_net=float(sub(asis).pnl.sum()),
  padded_trades=len(sub(pad)),padded_net=float(sub(pad).pnl.sum()),
  open_at_last_bar=int(sum(1 for r in sub(pad).itertuples() if r.xk>short[r.d])),
  full_total_asis=float(asis.pnl.sum()),full_total_pad=float(pad.pnl.sum()))
c=H.candace(); R['idea6']['candace_trades_on_short_days']=int(c.d.isin(sd).sum()); R['idea6']['candace_net']=float(c[c.d.isin(sd)].pnl.sum())
json.dump(R,open('/home/user/paytience/docs/results/agent_review_2026-11-24/refine_round2/results_r2.json','w'),indent=1,default=str)
print(json.dumps({k:R[k] for k in('idea6',)},default=str)); print(sorted(short.items())[:40])
for n in('idea1','idea3'): print(n,R[n]['picked'],R[n].get('pass'),R[n].get('control_p95_net_pf')); 
for n in('idea1','idea3'):
    for k,r in R[n]['rows'].items(): print(k,r['pick']['n'],r['pick']['pf'],r['pick']['net'],'|',r['judge']['n'],r['judge']['pf'],r['judge']['net'])
print(R['base'])
