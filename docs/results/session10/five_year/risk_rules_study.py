import sys, json, statistics as st
sys.path.insert(0,'/home/user/opogabuuga/backend')
from pathlib import Path
from datetime import date
from multiprocessing import Pool
from app.config import load_rules
from app.backtest.income_projection import rules_view, eval_view, research_days

PLANS={'pro25k':('lucid_pro_25k',1),'pro50k':('lucid_pro_50k',2),'pro100k':('lucid_pro_100k',2)}
SPLIT='2024-01-01'
names,days=research_days()
DAYS=[(date.fromisoformat(n).isocalendar()[:2],[float(x) for x in t]) for n,t in zip(names,days)]
NM=list(names)

def load(plan):
    r=load_rules(Path(f'/home/user/opogabuuga/config/rules/{plan}.yaml')).rules
    ev,fv=eval_view(r),rules_view(r)
    f=lambda v:{k:(float(x) if hasattr(x,'quantize') else x) for k,x in v.__dict__.items()}
    return f(ev),f(fv)

class Sizer:
    """account-level rules, shared by eval & funded. m=MLL, all $ thresholds are fractions of MLL."""
    def __init__(s,R,m,qty):
        s.R=R;s.m=m;s.qty=qty;s.skip=0;s.wk=None;s.wpnl=0.0;s.wstopped=False;s.paused_arm=True;s.last_day=0.0
    def start_day(s,wk,cushion,cycle_profit,target=None,remaining=None):
        R=s.R;q=s.qty;m=s.m
        if wk!=s.wk: s.wk=wk;s.wpnl=0.0;s.wstopped=False
        if s.skip>0: s.skip-=1; return 0
        if s.wstopped: return 0
        b=R.get('brake')
        if b:
            below=cushion<b['y']*m
            if below and b['act']=='pause' and s.paused_arm:
                s.paused_arm=False;s.skip=b['k']-1;return 0
            if not below: s.paused_arm=True
            if below and b['act']=='cut': q=1
        pl=R.get('plock')
        if pl is not None and cycle_profit>=pl*(target if target else m): q=1
        if target is not None and 'vdown' in R and remaining is not None and remaining<=R['vdown']*target: q=1
        return max(1,min(q,s.qty))
    def after_trade(s,day,ntrades_loss):
        R=s.R;m=s.m
        if 'dn' in R and ntrades_loss>=R['dn']: return True
        if 'dusd' in R and day<=-R['dusd']*m: return True
        return False
    def end_day(s,day,had):
        R=s.R;m=s.m
        s.wpnl+=day
        if 'wusd' in R and s.wpnl<=-R['wusd']*m: s.wstopped=True
        if had and 'cool' in R and day<=-R['cool']*m: s.skip=1

def eval_path(seq,r,qty,R,horizon=120):
    m=r['mll'];sz=Sizer(R,m,qty)
    bal=peak=r['start'];floor=bal-m;pos=[]
    for n,(wk,trades) in enumerate(seq[:horizon]):
        prof=bal-r['start']
        q=sz.start_day(wk,bal-floor,prof,r['target'],r['target']-prof)
        day=0.0;nl=0;had=False
        if q>0:
            for p in trades:
                p*=q;had=True
                if r['dll'] and day+p<=-r['dll']: p=-r['dll']-day
                bal+=p;day+=p
                if p<0: nl+=1
                if bal<=floor: return 'BUST',n+1
                if r['dll'] and day<=-r['dll']: break
                if sz.after_trade(day,nl): break
                if 'wprof' in R and day>=R['wprof']*r['target']: break
        sz.end_day(day,had)
        if trades and q>0: pos.append(day)
        peak=max(peak,bal)
        floor=r['lock_level'] if peak>=r['lock_trigger'] else max(floor,peak-m)
        prof=bal-r['start']
        if prof>=r['target'] and sum(1 for x in pos if x>0)>=r['min_profitable_days']:
            cons=r['consistency_pct']
            if cons is None or max(pos,default=0)<=cons/100*prof: return 'PASS',n+1
    return 'OPEN',min(horizon,len(seq))

def payout_amount(r,bal,cycle,n_paid):
    cp=sum(cycle)
    if cp<r['min_cycle_profit'] or cp<=0: return 0.0
    if r['consistency_pct'] is not None and max(cycle)>r['consistency_pct']/100*cp: return 0.0
    if r['min_profitable_days'] and sum(1 for x in cycle if x>=r['min_day_profit'])<r['min_profitable_days']: return 0.0
    amt=bal-r['buffer']
    cap=r['max_first'] if n_paid==0 else r['max_next']
    if cap is not None: amt=min(amt,cap)
    return amt if amt>=r['min_request'] else 0.0

def funded_path(seq,r,qty,R,cadence=10):
    m=r['mll'];sz=Sizer(R,m,qty)
    bal=peak=r['start'];floor=bal-m;cycle=[];paid=0.0;np_=0
    for n,(wk,trades) in enumerate(seq):
        q=sz.start_day(wk,bal-floor,sum(cycle))
        day=0.0;nl=0;had=False
        if q>0:
            for p in trades:
                p*=q;had=True
                if r['dll'] is not None and day+p<=-r['dll']: p=-r['dll']-day
                bal+=p;day+=p
                if p<0: nl+=1
                if bal<=floor: return paid,'BUST',n+1,np_
                if r['dll'] is not None and day<=-r['dll']: break
                if sz.after_trade(day,nl): break
        sz.end_day(day,had)
        if trades and q>0: cycle.append(day)
        peak=max(peak,bal)
        floor=r['lock_level'] if peak>=r['lock_trigger'] else max(floor,peak-m)
        if (n+1)%cadence==0 and np_<r['max_payouts']:
            a=payout_amount(r,bal,cycle,np_)
            if a>0:
                bal-=a;paid+=a*r['split'];np_+=1;cycle=[]
                if r['lock_mll_on_payout']: floor=max(floor,r['lock_level'])
        if np_>=r['max_payouts']: return paid,'MAX',n+1,np_
    return paid,'OPEN',len(seq),np_

VARIANTS={
 'baseline':{},
 'D1 stop after 2 losing trades':{'dn':2},
 'D2 stop after 1 losing trade':{'dn':1},
 'D3 day loss 0.25xMLL':{'dusd':.25},
 'D4 day loss 0.40xMLL':{'dusd':.40},
 'W1 week loss 0.5xMLL':{'wusd':.5},
 'W2 week loss 0.8xMLL':{'wusd':.8},
 'B1 brake cush<30% cut->1':{'brake':{'y':.3,'act':'cut'}},
 'B2 brake cush<50% cut->1':{'brake':{'y':.5,'act':'cut'}},
 'B3 brake cush<30% pause 3':{'brake':{'y':.3,'act':'pause','k':3}},
 'B4 brake cush<50% pause 5':{'brake':{'y':.5,'act':'pause','k':5}},
 'P1 profit lock 0.6xMLL cycle->1':{'plock':.6},
 'P2 profit lock 0.3xMLL cycle->1':{'plock':.3},
 'C1 cool-off lose>0.3xMLL':{'cool':.3},
 'C2 cool-off lose>0.15xMLL':{'cool':.15},
 'E1 eval day profit>=25% tgt stop':{'wprof':.25},
 'E2 eval day profit>=40% tgt stop':{'wprof':.40},
 'E3 eval size down within 30% tgt':{'vdown':.3},
 'E4 eval size down within 15% tgt':{'vdown':.15},
 'X1 D4+B2':{'dusd':.4,'brake':{'y':.5,'act':'cut'}},
 'X2 D3+C1+W2':{'dusd':.25,'cool':.3,'wusd':.8},
 'X3 D4+B2+P1':{'dusd':.4,'brake':{'y':.5,'act':'cut'},'plock':.6},
}
# eval-only keys are harmless in funded (ignored) -> eval-only variants tagged
EVAL_ONLY={k for k in VARIANTS if k.startswith('E')}

def run(args):
    pk,vn=args
    plan,qty=PLANS[pk];ev,fv=load(plan);R=VARIANTS[vn]
    res={'plan':pk,'var':vn}
    # eval
    L=len(DAYS)
    st_e=list(range(0,L-120,2));out=[]
    for i in st_e: out.append((i,)+eval_path(DAYS[i:i+120],ev,qty,R))
    def ev_stats(sel):
        n=len(sel);
        return {'n':n,'pass':100*sum(o[1]=='PASS' for o in sel)/n,'bust':100*sum(o[1]=='BUST' for o in sel)/n,
                'med_days':st.median([o[2] for o in sel if o[1]=='PASS']) if any(o[1]=='PASS' for o in sel) else None}
    res['eval']={'all':ev_stats(out),'h1':ev_stats([o for o in out if NM[o[0]]<SPLIT]),'h2':ev_stats([o for o in out if NM[o[0]]>=SPLIT])}
    if vn in EVAL_ONLY: res['fund']=None;return res
    st_f=list(range(0,L-260,2));fo=[(i,)+funded_path(DAYS[i:i+260],fv,qty,R) for i in st_f]
    def f_stats(sel):
        n=len(sel);paid=[o[1]*5 for o in sel]
        return {'n':n,'mean_2wk':sum(paid)/n/(260/10),'year_med':st.median(paid),'year_mean':sum(paid)/n,'bust':100*sum(o[2]=='BUST' for o in sel)/n}
    res['fund']={'all':f_stats(fo),'h1':f_stats([o for o in fo if NM[o[0]]<SPLIT]),'h2':f_stats([o for o in fo if NM[o[0]]>=SPLIT])}
    return res

if __name__=='__main__':
    jobs=[(p,v) for p in PLANS for v in VARIANTS]
    with Pool(4) as pool: rs=pool.map(run,jobs,chunksize=1)
    json.dump(rs,open('results.json','w'),indent=1)
    print('done',len(rs))
