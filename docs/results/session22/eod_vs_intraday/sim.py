import numpy as np, pandas as pd, yaml, glob, os
R='/home/user/opogabuuga/'
ERAS={'all':('2019-05-06','2026-11-06'),'is':('2019-05-06','2025-11-05'),'j':('2025-11-06','2026-11-06')}
def load_streams():
    n=pd.read_csv(R+'docs/results/session19/refine/streams_noise_R6.csv')
    f=pd.read_csv(R+'docs/results/session19/refine/streams_fade_F0.csv')
    f['risk']=250.0   # fade file has no risk column: assume same $250 per-micro broker stop
    f=f[pd.to_datetime(f.d).dt.dayofweek!=0]
    f=f[~f.d.isin(set(n.d))]
    return n,f[['d','ek','pnl','mae','risk','side']]
def day_table(df,era):
    a,b=ERAS[era]; days=pd.bdate_range(a,b)
    g={k:v.sort_values('ek')[['pnl','mae','risk']].values.tolist() for k,v in df.groupby('d')}
    return [g.get(d.strftime('%Y-%m-%d'),[]) for d in days]
def load_plans():
    P={}
    for p in sorted(glob.glob(R+'config/rules/lucid_*.yaml')):
        d=yaml.safe_load(open(p)); e=d['eval']; s=d.get('strategy',{}); it=d.get('internal',{})
        size=d['account_size']; tabs={}
        for nm,k in(('regular','size_table'),('suggested','size_table_suggested'),('high','size_table_high')):
            row=next((r for r in (s.get(k) or []) if r['account_size']==size),None)
            tabs[nm]=row or {'contracts':1}
        nm=os.path.basename(p)[:-5]; cons=e['consistency_max_day_pct']; dll=e['daily_loss_limit']; scale=False
        if nm.startswith('lucid_pro_'):   # Pro rules (2026-11-13); YAMLs final, assert they match
            assert cons==40 and dll=={25000:600,50000:1200,100000:1800,150000:2700}[size] and e.get('dll_scale_above_lock_pct')==60,(nm,cons,dll)
            scale=True
        P[nm]=dict(scale=scale,buf=it.get('consistency_day_stop_buffer_pct',5),size=size,target=e['profit_target'],mll=e['max_loss_limit'],lock_trig=e['lock_trigger'],
            lock_lvl=e['lock_level'],dll=dll,cons=cons,mpd=e['min_profitable_days'],
            kill=it.get('kill_switch_mll_distance',50),margin=it.get('dll_safety_margin',40),tabs=tabs)
    return P
def sim_path(days,idx,pl,row,mode_on,room=True,kill=None,margin=None,maxs=400):
    kd=pl['kill'] if kill is None else kill; mg=pl['margin'] if margin is None else margin
    bal=pl['size']; floor=bal-pl['mll']; peak=bal; locked=False; mll=pl['mll']
    dll=pl['dll']; prof_days=0; best=0.0; s=0
    cn=row['contracts']; bb=row.get('brake_below'); bc=row.get('brake_contracts')
    for di in idx[:maxs]:
        s+=1; today=0.0; stop=False; dead=None
        for pnl,mae,risk in days[di]:
            if stop: break
            q=cn
            if bb is not None and (bal-floor)/mll<bb: q=bc
            if room:
                r=bal-floor-kd
                if dll: r=min(r,dll+today)
                while q>0 and q*risk+mg>r: q-=1
                if q==0:
                    if bal-floor-kd<risk+mg: return 'stuck',s   # no later trade can ever fit
                    continue
            p=q*pnl
            if not mode_on and kd>=0 and q*mae>=bal-floor-kd:
                p=-(bal-floor-kd); dead='kill'
            elif mode_on:
                pass
            if dll and today+p<=-dll: p=-dll-today; stop=True
            today+=p; bal+=p
            if dead: return 'bust',s
            if mode_on and bal<=floor+kd: return 'bust',s
            if (not mode_on) and bal<=floor+kd and kd>0: return 'bust',s
            if dll and today<=-dll: stop=True
        # end of day
        if today>0: prof_days+=1; best=max(best,today)
        if bal>peak and not locked:
            peak=bal
            if peak>=pl['lock_trig']: locked=True; floor=pl['lock_lvl']
            else: floor=peak-mll
        prof=bal-pl['size']
        if prof>=pl['target'] and prof_days>=pl['mpd'] and (not pl['cons'] or best<=pl['cons']/100*prof):
            return 'pass',s
    return 'open',s
def make_paths(n,paths=600,sess=400,blk=10,seed=7):
    rng=np.random.default_rng(seed); nb=-(-sess//blk)
    st=rng.integers(0,n-blk+1,size=(paths,nb))
    return [np.concatenate([np.arange(a,a+blk) for a in r])[:sess] for r in st]
def run_cfg(days,paths,pl,row,mode_on,**kw):
    c={'pass':0,'bust':0,'stuck':0,'open':0}; ps=[]
    for idx in paths:
        o,s=sim_path(days,idx,pl,row,mode_on,**kw); c[o]+=1
        if o=='pass': ps.append(s)
    N=len(paths)
    return {'pass':100*c['pass']/N,'bust':100*(c['bust']+c['stuck'])/N,'stuck':100*c['stuck']/N,'open':100*c['open']/N,
            'days':float(np.median(ps)) if ps else 0}
