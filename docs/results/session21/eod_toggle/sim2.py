import sys,os,math,pickle; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
from sim import load_plans
R='/home/user/opogabuuga/'
PKL='/tmp/claude-0/-home-user-opogabuuga/50bc3d78-c0a4-5955-9229-af69d0b1b2e9/scratchpad/data/days12.pkl'
ERAS={'all':('2021-10-21','2026-10-30'),'is':('2021-10-21','2025-11-05'),'j':('2025-11-06','2026-10-30')}
SHRINK=0.6; MINPCT=0.002; TV=0.5; FEE=1.0; SLIP=1
def load():
    D,_=pickle.load(open(PKL,'rb')); op={d:a['open'] for d,a in D}
    t=pd.read_csv(R+'docs/results/session20/strategy_review/streams_BASE.csv')
    t['entry']=[float(op[d][int(k)]) for d,k in zip(t.d,t.ek)]
    return t
def day_table(t,era):
    a,b=ERAS[era]; days=pd.bdate_range(a,b)
    g={k:v.sort_values('ek')[['pnl','mae','risk','entry']].values.tolist() for k,v in t.groupby('d')}
    return [g.get(d.strftime('%Y-%m-%d'),[]) for d in days]
def make_paths(L,paths=600,cap=400,block=10,seed=7):
    # session-20 protocol (lib.eval_boot): uniform start in [0,L), short blocks at the tail
    rnd=np.random.default_rng(seed); out=[]
    for _ in range(paths):
        p=[]
        while len(p)<cap:
            i=int(rnd.integers(0,L)); p.extend(range(i,min(i+block,L)))
        out.append(np.array(p[:cap]))
    return out
def smin(entry): # smallest allowed per-micro S' ($)
    pt=math.ceil(MINPCT*entry/0.25-1e-9); return pt*TV+FEE+TV
def sim_path(days,idx,pl,row,mode_on,shrink=True,room=True,kill=None,margin=None,maxs=400,gmin=None):
    kd=pl['kill'] if kill is None else kill; mg=pl['margin'] if margin is None else margin
    bal=pl['size']; floor=bal-pl['mll']; peak=bal; locked=False; mll=pl['mll']
    dll=pl['dll']; pdays=0; best=0.0; s=0
    cn=row['contracts']; bb=row.get('brake_below'); bc=row.get('brake_contracts')
    for di in idx[:maxs]:
        s+=1; today=0.0; stop=False
        for pnl,mae,risk,entry in days[di]:
            if stop: break
            q=cn
            if bb is not None and (bal-floor)/mll<bb: q=bc
            p=None; eff_mae=mae
            if room:
                if bal-floor<=kd: return 'stuck',s
                room0=bal-floor-kd
                if dll: room0=min(room0,dll+today)
                while q>0:
                    S=risk
                    if shrink and q*risk>SHRINK*room0:
                        pt=math.floor(((SHRINK*room0/q)-FEE)/TV-SLIP)
                        if pt*0.25<MINPCT*entry or pt<=0: q=-1;break
                        S=pt*TV+FEE+TV
                    if q*S+mg<=room0:
                        if S<risk and mae>=S: p=-S; eff_mae=S
                        else: p=pnl
                        eff_mae=min(mae,S) if S<risk else mae
                        break
                    q-=1
                if q<=0:
                    # nothing fits: stuck if even the best case can never fit later
                    if shrink:
                        if SHRINK*(bal-floor-kd)<gmin: return 'stuck',s
                    elif bal-floor-kd<risk+mg: return 'stuck',s
                    continue
            else: p=pnl
            pq=q*p
            dead=False
            if not mode_on and kd>=0 and q*eff_mae>=bal-floor-kd:
                pq=-(bal-floor-kd); dead=True
            if dll and today+pq<=-dll: pq=-dll-today; stop=True
            today+=pq; bal+=pq
            if dead: return 'bust',s
            if bal<=floor+kd: return 'bust',s
        if today>0: pdays+=1; best=max(best,today)
        if bal>peak and not locked:
            peak=bal
            if peak>=pl['lock_trig']: locked=True; floor=pl['lock_lvl']
            else: floor=peak-mll
        prof=bal-pl['size']
        if prof>=pl['target'] and pdays>=pl['mpd'] and (not pl['cons'] or best<=pl['cons']/100*prof): return 'pass',s
    return 'open',s
GMIN=None
def run_cfg(days,paths,pl,row,mode_on,**kw):
    gmin=GMIN
    c={'pass':0,'bust':0,'stuck':0,'open':0}; ps=[]
    for idx in paths:
        o,s=sim_path(days,idx,pl,row,mode_on,gmin=gmin,**kw); c[o]+=1
        if o=='pass': ps.append(s)
    N=len(paths)
    return {'pass':100*c['pass']/N,'bust':100*(c['bust']+c['stuck'])/N,'stuck':100*c['stuck']/N,'open':100*c['open']/N,'days':float(np.median(ps)) if ps else 0}
