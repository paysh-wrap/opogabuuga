import sys, itertools, json
sys.path.insert(0,'/home/user/opogabuuga/backend')
from decimal import Decimal
from pathlib import Path
from statistics import median
import numpy as np, pandas as pd
from app.config import load_rules
from app.backtest import income_projection as ip

BARS='/tmp/claude-0/-home-user-opogabuuga/528f0293-22e9-5e48-80a8-65343eb6ade7/scratchpad/data/mnq_5y.csv'
Z=Decimal(0)

def daily_vol_inputs():
    df=pd.read_csv(BARS,usecols=['timestamp','close'])
    ts=pd.to_datetime(df.timestamp,utc=True).dt.tz_convert('America/New_York')
    df['ts']=ts; df=df.set_index('ts')
    rth=df.between_time('09:30','15:59')
    close=rth.close.groupby(rth.index.date).last()
    close.index=pd.to_datetime(close.index)
    return close.pct_change().dropna()   # RTH close-to-close return, indexed by day

def per_day_vol(rets,names,win):
    # vol known BEFORE day D: std of last `win` returns dated < D
    s=rets.rolling(win).std().dropna()
    idx=s.index; vals=s.values
    out=[]
    for n in names:
        d=pd.Timestamp(n); k=idx.searchsorted(d)-1  # last vol dated < d
        out.append((idx[k],vals[k]) if k>=0 else (None,None))
    return out, s

def contracts(names,rets,win,target,base,mx):
    pv,s=per_day_vol(rets,names,win)
    ins=s[(s.index>='2021-11-01')&(s.index<='2023-12-31')].median()
    q=[]
    for n,(dt,v) in zip(names,pv):
        if v is None: q.append(base); continue
        d=pd.Timestamp(n)
        if target=='insample': t=ins
        else:
            w=s[(s.index>=d-pd.Timedelta(days=365))&(s.index<d)]
            t=w.median() if len(w)>=60 else s[s.index<d].median() if (s.index<d).sum()>=20 else v
        q.append(int(max(1,min(mx,round(base*t/v)))))
    return q

def funded_path(days,qs,r,cadence,brake):
    bal=peak=r.start; floor=r.start-r.mll; cycle=[]; paid=Z; pays=[]
    for n,trades in enumerate(days):
        day=Z; qty=qs[n]
        if brake is not None and bal-floor<brake[0]*r.mll: qty=min(qty,brake[1])
        for p in trades:
            p*=qty
            if r.dll is not None and day+p<=-r.dll: p=-r.dll-day
            bal+=p; day+=p
            if bal<=floor: return ip.Path1(paid,tuple(pays),'BUST',n+1)
            if r.dll is not None and day<=-r.dll: break
        if trades: cycle.append(day)
        peak=max(peak,bal)
        floor=r.lock_level if peak>=r.lock_trigger else max(floor,peak-r.mll)
        if (n+1)%cadence==0 and (r.max_payouts is None or len(pays)<r.max_payouts):
            amt=ip.payout_amount(r,bal,cycle,len(pays))
            if amt>0:
                bal-=amt; mine=(amt*r.split).quantize(ip.CENT); paid+=mine; pays.append((n+1,mine)); cycle=[]
                if r.lock_mll_on_payout: floor=max(floor,r.lock_level)
        if r.max_payouts is not None and len(pays)>=r.max_payouts: return ip.Path1(paid,tuple(pays),'MAX_PAYOUTS',n+1)
    return ip.Path1(paid,tuple(pays),'OPEN',len(days))

def eval_path(days,qs,r,horizon,brake):
    bal=peak=r.start; floor=r.start-r.mll; pos=[]
    for n,trades in enumerate(days[:horizon]):
        day=Z; q=qs[n]
        if brake is not None and bal-floor<brake[0]*r.mll: q=min(q,brake[1])
        for p in trades:
            p*=q
            if r.dll is not None and day+p<=-r.dll: p=-r.dll-day
            bal+=p; day+=p
            if bal<=floor: return 'BUST'
            if r.dll is not None and day<=-r.dll: break
        if trades: pos.append(day)
        peak=max(peak,bal)
        floor=r.lock_level if peak>=r.lock_trigger else max(floor,peak-r.mll)
        prof=bal-r.start
        if prof>=r.target and sum(1 for x in pos if x>0)>=r.min_profitable_days and (r.consistency_pct is None or max(pos,default=Z)<=r.consistency_pct/100*prof): return 'PASS'
    return 'OPEN'

SPLIT=pd.Timestamp('2024-01-01')
def run(plan,qs_all,brake,accounts=5):
    rules=load_rules(Path(f'/home/user/opogabuuga/config/rules/lucid_pro_{plan}k.yaml')).rules
    fr=ip.rules_view(rules); ev=ip.eval_view(rules)
    names,days=ip.research_days(); days=list(days)
    res={}
    for kind,H in (('funded',260),('eval',250)):
        rows=[]
        for i in range(0,max(1,len(days)-H),2):
            d=days[i:i+H]; q=qs_all[i:i+H]
            if kind=='funded':
                p=funded_path(d,q,fr,10,brake); rows.append((names[i],float(p.paid*accounts),p.status))
            else: rows.append((names[i],0,eval_path(d,q,ev,H,brake)))
        res[kind]=rows
    def agg(rows,sel):
        rows=[r for r in rows if sel(pd.Timestamp(r[0]))]
        return rows
    out={}
    for half,sel in (('all',lambda t:True),('H1',lambda t:t<SPLIT),('H2',lambda t:t>=SPLIT)):
        f=agg(res['funded'],sel); e=agg(res['eval'],sel)
        paid=[x[1] for x in f]
        out[half]=dict(n=len(f),per2w=np.mean(paid)/26,mean=np.mean(paid),med=float(np.median(paid)),p25=float(np.percentile(paid,25)),
                       bust=100*np.mean([x[2]=='BUST' for x in f]),
                       eval_pass=100*np.mean([x[2]=='PASS' for x in e]),eval_bust=100*np.mean([x[2]=='BUST' for x in e]))
    return out

if __name__=='__main__':
    names,days=ip.research_days(); names=list(names)
    rets=daily_vol_inputs()
    plans={ '150':[(3,(Decimal('0.5'),2)),(4,(Decimal('0.5'),2))], '100':[(2,(Decimal('0.3'),1))] }
    allres=[]
    for plan,lst in plans.items():
        for base,brk in lst:
            for brake_on in (True,False):
                b=brk if brake_on else None
                r=run(plan,[base]*len(names),b)
                allres.append(dict(plan=plan,base=base,brake=brake_on,variant='BASE',res=r)); print(plan,base,brake_on,'BASE',json.dumps({k:{a:round(c,1) for a,c in v.items()} for k,v in r.items()}),flush=True)
                for win,tg in itertools.product((14,20),('prior1y','insample')):
                    qs=contracts(names,rets,win,tg,base,base+2)
                    r=run(plan,qs,b)
                    allres.append(dict(plan=plan,base=base,brake=brake_on,variant=f'vol{win}-{tg}',res=r,avgq=float(np.mean(qs))))
                    print(plan,base,brake_on,win,tg,round(np.mean(qs),2),json.dumps({k:{a:round(c,1) for a,c in v.items()} for k,v in r.items()}),flush=True)
    json.dump(allres,open('results.json','w'),indent=1)
