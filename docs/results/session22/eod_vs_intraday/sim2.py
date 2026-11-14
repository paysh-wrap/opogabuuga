import sys,os,math,pickle; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
from sim import load_plans
R='/home/user/opogabuuga/'
PKL='/tmp/claude-0/-home-user-opogabuuga/13cb35fb-f8d0-52e2-a7d8-3c5c31ee09a8/scratchpad/data/days12.pkl'
ERAS={'all':('2021-10-21','2026-10-30'),'is':('2021-10-21','2025-11-05'),'j':('2025-11-06','2026-10-30')}
SHRINK=0.6; MINPCT=0.002; TV=0.5; FEE=1.0; SLIP=1
def load():
    D,_=pickle.load(open(PKL,'rb')); op={d:a['open'] for d,a in D}
    t=pd.read_csv(R+'docs/results/session20/strategy_review/streams_BASE.csv')
    t['entry']=[float(op[d][int(k)]) for d,k in zip(t.d,t.ek)]
    return t
def load_fade(t):
    D,_=pickle.load(open(PKL,'rb')); op={d:a['open'] for d,a in D}
    f=pd.read_csv(R+'docs/results/session19/refine/streams_fade_F0.csv'); f['risk']=250.0
    f=f[(f.d>='2021-10-21')&(f.d<='2026-10-30')]
    f=f[pd.to_datetime(f.d).dt.dayofweek!=0]; f=f[~f.d.isin(set(t.d))]
    f['entry']=[float(op[d][int(k)]) for d,k in zip(f.d,f.ek)]
    return pd.concat([t[['d','ek','pnl','mae','risk','entry']],f[['d','ek','pnl','mae','risk','entry']]])
def day_table(t,era):
    a,b=ERAS[era]; days=pd.bdate_range(a,b)
    t=t.copy(); t['pth']=[PATHS[(d,int(k))] for d,k in zip(t.d,t.ek)]
    g={k:v.sort_values('ek')[['pnl','mae','risk','entry','pth']].values.tolist() for k,v in t.groupby('d')}
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
    dll0=pl['dll']; dll=dll0; pdays=0; best=0.0; s=0; peak_e=bal
    dstop=(pl['cons']-pl['buf'])/100*pl['target'] if pl['cons'] else None
    cn=row['contracts']; bb=row.get('brake_below'); bc=row.get('brake_contracts')
    for di in idx[:maxs]:
        s+=1; today=0.0; stop=False
        dll=dll0
        if pl['scale'] and locked: dll=0.6*(peak_e-pl['size'])
        for pnl,mae,risk,entry,_pth in days[di]:
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
            if dstop is not None and today+pq>dstop: pq=dstop-today; stop=True
            today+=pq; bal+=pq
            if dead: return 'bust',s
            if bal<=floor+kd: return 'bust',s
        if today>0: pdays+=1; best=max(best,today)
        peak_e=max(peak_e,bal)
        if bal>peak and not locked:
            peak=bal
            if peak>=pl['lock_trig']: locked=True; floor=pl['lock_lvl']
            else: floor=peak-mll
        prof=bal-pl['size']
        if prof>=pl['target'] and pdays>=pl['mpd'] and (not pl['cons'] or best<=pl['cons']/100*prof): return 'pass',s
    return 'open',s
PATHS={}
GMIN=None
def run_cfg(days,paths,pl,row,mode_on,**kw):
    gmin=GMIN
    c={'pass':0,'bust':0,'stuck':0,'open':0}; ps=[]
    for idx in paths:
        o,s=sim_path(days,idx,pl,row,mode_on,gmin=gmin,**kw); c[o]+=1
        if o=='pass': ps.append(s)
    N=len(paths)
    return {'pass':100*c['pass']/N,'bust':100*(c['bust']+c['stuck'])/N,'stuck':100*c['stuck']/N,'open':100*c['open']/N,'days':float(np.median(ps)) if ps else 0}


def build_paths(t,order='heur'):
    """per trade: time-ordered open P&L per micro ($) at each bar extreme (1-min bars ek..xk), same window as the stream's MAE.
    adverse extreme carries the stream's extra tick slippage (-0.5), so min(path) = -mae exactly."""
    D,_=pickle.load(open(PKL,'rb')); d_={d:a for d,a in D}; out={}
    for _,r in t.iterrows():
        a=d_[r.d]; e=int(r.ek); x=int(r.xk); s=int(r.side); en=a['open'][e]+s*0.25
        def mae_w(w):
            l=a['low'][e:w]; h=a['high'][e:w]
            return (max(0,(en-l.min())) if s==1 else max(0,(h.max()-en)))*2+0.5
        w=x+1 if abs(mae_w(x+1)-r.mae)<.01 else x
        o=a['open'][e:w]; c=a['close'][e:w]; hi=a['high'][e:w]; lo=a['low'][e:w]
        if s==1: adv=np.minimum(0,(lo-en)*2)-0.5; fav=(hi-en)*2
        else: adv=np.minimum(0,(en-hi)*2)-0.5; fav=(en-lo)*2
        up=(c>=o)==(s==1) if order=='heur' else np.full(len(o),order=='best')   # bar closes in the trade's favour -> adverse extreme first (O-L-H-C for a long)
        first=np.where(up,adv,fav); second=np.where(up,fav,adv)
        pth=np.empty(2*len(o)+1); pth[0:-1:2]=first; pth[1:-1:2]=second; pth[-1]=r.pnl
        out[(r.d,int(r.ek))]=pth
    return out

def sim_intra(days,idx,pl,row,shrink=True,kill=None,margin=None,maxs=400,gmin=None,trace=False):
    """Intraday trailing: floor = max equity (balance + open P&L) so far - MLL, continuous; locks at lock_lvl once that peak >= lock_trigger.
    Kill switch on equity (balance + open P&L) within kd of the current floor. Returns outcome, sessions, info."""
    kd=pl['kill'] if kill is None else kill; mg=pl['margin'] if margin is None else margin
    bal=pl['size']; floor=bal-pl['mll']; locked=False; mll=pl['mll']; LT=pl['lock_trig']; LL=pl['lock_lvl']
    eodpeak=bal; eodlocked=False
    dll0=pl['dll']; pdays=0; best=0.0; s=0; peak_e=bal
    dstop=(pl['cons']-pl['buf'])/100*pl['target'] if pl['cons'] else None
    cn=row['contracts']; bb=row.get('brake_below'); bc=row.get('brake_contracts')
    def eodfloor(): return LL if eodpeak>=LT else eodpeak-mll
    for di in idx[:maxs]:
        s+=1; today=0.0; stop=False; dll=dll0
        if pl['scale'] and locked: dll=0.6*(peak_e-pl['size'])
        for pnl,mae,risk,entry,pth in days[di]:
            if stop: break
            q=cn
            if bb is not None and (bal-floor)/mll<bb: q=bc
            p=None
            if bal-floor<=kd: return 'stuck',s,dict(raised=floor>eodfloor()+1e-9,cause='stuck')
            room0=bal-floor-kd
            if dll: room0=min(room0,dll+today)
            S=risk
            while q>0:
                S=risk
                if shrink and q*risk>SHRINK*room0:
                    pt=math.floor(((SHRINK*room0/q)-FEE)/TV-SLIP)
                    if pt*0.25<MINPCT*entry or pt<=0: q=-1;break
                    S=pt*TV+FEE+TV
                if q*S+mg<=room0:
                    p=-S if (S<risk and mae>=S) else pnl
                    break
                q-=1
            if q<=0:
                if shrink:
                    if SHRINK*(bal-floor-kd)<gmin: return 'stuck',s,dict(raised=floor>eodfloor()+1e-9,cause='stuck')
                elif bal-floor-kd<risk+mg: return 'stuck',s,dict(raised=floor>eodfloor()+1e-9,cause='stuck')
                continue
            u=pth
            if S<risk and mae>=S:        # shrunk stop is hit: path ends there
                j=int(np.argmax(-u>=S)); u=np.append(u[:j],-S)
            eq=bal+q*u
            rm=np.maximum.accumulate(eq)
            fl=np.maximum(floor,rm-mll) if not locked else np.full(len(eq),floor)
            if not locked:
                fl=np.where(rm>=LT,LL,fl)
            hit=np.nonzero(eq<=fl+kd)[0]
            if len(hit):
                j=hit[0]
                only=bool(np.min(eq[:j+1])>eodfloor()+kd)   # the EOD-trailing floor would NOT have been touched
                return 'bust',s,dict(raised=floor>eodfloor()+1e-9,cause='kill',only_intraday=only,mfe_peak=float(rm[j]-bal))
            pq=q*p
            if dll and today+pq<=-dll: pq=-dll-today; stop=True
            if dstop is not None and today+pq>dstop: pq=dstop-today; stop=True
            today+=pq; bal+=pq
            floor=float(fl[-1]); 
            if rm[-1]>=LT: locked=True
            if bal<=floor+kd: return 'bust',s,dict(raised=floor>eodfloor()+1e-9,cause='post',only_intraday=False)
        if today>0: pdays+=1; best=max(best,today)
        peak_e=max(peak_e,bal); eodpeak=max(eodpeak,bal)
        prof=bal-pl['size']
        if prof>=pl['target'] and pdays>=pl['mpd'] and (not pl['cons'] or best<=pl['cons']/100*prof): return 'pass',s,{}
    return 'open',s,{}

def agg(res,N):
    c={'pass':0,'bust':0,'stuck':0,'open':0}; ps=[]
    for o,s,_ in res:
        c[o]+=1
        if o=='pass': ps.append(s)
    return {'pass':100*c['pass']/N,'bust':100*(c['bust']+c['stuck'])/N,'stuck':100*c['stuck']/N,'open':100*c['open']/N,'days':float(np.median(ps)) if ps else 0}
