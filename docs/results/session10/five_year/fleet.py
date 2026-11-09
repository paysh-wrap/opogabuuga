import sys, dataclasses, statistics as st
sys.path.insert(0,'/home/user/opogabuuga/backend')
from decimal import Decimal as D
from pathlib import Path
from app.config import load_rules
from app.backtest.income_projection import *
from app.backtest.income_projection import ZERO
names, DAYS = research_days(); N=len(DAYS)
H=520; WARM=130
PLANS={ # funded (base,brake), eval (base,grow,max,brake,daylock)
 '25K':(1,None, 1,None,5,None,False),
 '50K':(2,(D('.5'),1), 2,None,5,(D('.5'),1),False),
 '100K':(2,(D('.3'),1), 2,D(1200),4,(D('.3'),1),True),
 '150K':(3,(D('.5'),2), 4,None,5,(D('.5'),2),False),
 '150K-HR':(4,(D('.5'),2), 4,None,5,(D('.5'),2),False)}
def eval_dl(days,r,qty,grow,mx,brake,daylock,horizon=120):
    bal=peak=r.start; floor=r.start-r.mll; pos=[]
    for n,trades in enumerate(days[:horizon]):
        day=ZERO; sb=bal
        q=size_for(qty,bal-floor,grow,mx)
        if brake and bal-floor<brake[0]*r.mll: q=min(q,brake[1])
        lim=D('.33')*max(r.target-(sb-r.start),ZERO)
        for p in trades:
            p*=q
            if r.dll is not None and day+p<=-r.dll: p=-r.dll-day
            bal+=p; day+=p
            if bal<=floor: return "BUST",n+1
            if r.dll is not None and day<=-r.dll: break
            if daylock and day>=lim and lim>0: break
        if trades: pos.append(day)
        peak=max(peak,bal)
        floor=r.lock_level if peak>=r.lock_trigger else max(floor,peak-r.mll)
        prof=bal-r.start
        if prof>=r.target and sum(1 for x in pos if x>0)>=r.min_profitable_days and (r.consistency_pct is None or max(pos,default=ZERO)<=r.consistency_pct/100*prof): return "PASS",n+1
    return "OPEN",min(horizon,len(days))
def pct(xs,q):
    s=sorted(xs); return s[min(len(s)-1,int(q*(len(s)-1)+.5))]
def run(plan,stagger):
    fb,fbr,eb,eg,em,ebr,dl=PLANS[plan]
    rp=Path(f'/home/user/opogabuuga/config/rules/lucid_pro_{plan.split("-")[0].lower()}.yaml')
    R=load_rules(rp).rules; fv=dataclasses.replace(rules_view(R),max_payouts=5); ev=eval_view(R)
    fc={}; ec={}
    def FP(s):
        if s not in fc: fc[s]=funded_path(DAYS[s:s+H],fv,fb,10,brake=fbr)
        return fc[s]
    def EP(s):
        if s not in ec: ec[s]=eval_dl(DAYS[s:s+120],ev,eb,eg,em,ebr,dl)
        return ec[s]
    out=[]
    for f in range(0,N-H,5):
        end=f+H; blocks=[ZERO]*(H//10)
        evals=[]  # (start,endsession,res)
        dormant=0; queue=0; slots=[None]*5  # funded: (start,path)
        pending=[f+(10*i if stagger else 0) for i in range(5)]
        bought=[]; busts=[]; occ=[]
        evals_active=[]
        for t in range(f,end):
            # funded finishing
            for i,sl in enumerate(slots):
                if sl and sl[0]+sl[1].sessions<=t:
                    if sl[1].status=='BUST': busts.append(t)
                    slots[i]=None
            # evals finishing before t
            still=[]
            for (s,e,res) in evals_active:
                if e<t:
                    if res=='PASS': queue+=1
                    dormant+=1
                else: still.append((s,e,res))
            evals_active=still
            # fill funded
            for i in range(5):
                if slots[i] is None and queue>0:
                    p=FP(t); slots[i]=(t,p); queue-=1
                    for (idx,amt) in p.payouts:
                        g=t+idx-1
                        if g<end: blocks[(g-f)//10]+=amt
            # start evals
            for pt in list(pending):
                if pt<=t: pending.remove(pt); dormant+=1
            while dormant>0 and queue<5 and not any(False for _ in []):
                dormant-=1; res,n=EP(t); evals_active.append((t,t+n-1,res)); bought.append(t)
            if t-f>=WARM: occ.append(sum(1 for s in slots if s))
        sb=[b for b in bought if b-f>=WARM]; sbu=[b for b in busts if b-f>=WARM]
        out.append(dict(f=f,era=0 if names[f]<'2024-01-01' else 1,warm=blocks[:13],steady=blocks[13:],
            wbought=len([b for b in bought if b-f<WARM]),bought=len(sb),busts=len(sbu),occ=sum(occ)/len(occ)))
    return out
def summ(out,key=None):
    if key: out=[o for o in out if key(o)]
    sb=[float(x) for o in out for x in o['steady']]; wb=[float(x) for o in out for x in o['warm']]
    nb=len(out)*39; yrs=390/260
    ev=sum(o['bought'] for o in out)/nb; bu=sum(o['busts'] for o in out)/nb
    m=sum(sb)/len(sb)
    return dict(n=len(out),mean=m,med=st.median(sb),p25=pct(sb,.25),p75=pct(sb,.75),zero=100*sum(1 for x in sb if x==0)/len(sb),
      warm=sum(wb)/len(wb),occ=sum(o['occ'] for o in out)/len(out),evy=sum(o['bought'] for o in out)/len(out)/yrs,
      buy=sum(o['busts'] for o in out)/len(out)/yrs,evblk=ev,be=(m/ev if ev else 0))
if __name__=='__main__':
    L=[]
    for plan in PLANS:
        for stg in (False,True):
            o=run(plan,stg); a=summ(o); e1=summ(o,lambda x:x['era']==0); e2=summ(o,lambda x:x['era']==1)
            L.append((plan,stg,a,e1,e2)); print(plan,'stag' if stg else 'sync',{k:round(v,1) for k,v in a.items()},flush=True)
    import json; json.dump([(p,s,a,b,c) for p,s,a,b,c in L],open('res.json','w'))
