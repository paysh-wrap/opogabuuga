import sys,os,json,pickle; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from multiprocessing import Pool
import numpy as np
import sim2
from sim2 import *
P=load_plans(); t=load()
HERE=os.path.dirname(os.path.abspath(__file__))
ORD=os.environ.get('ORDER','heur')
sim2.PATHS.update(build_paths(t,ORD))
sim2.GMIN=smin(float(t[t.d>='2025-11-06'].entry.mean())); print('gmin',sim2.GMIN,'order',ORD)
T={}
for e in ERAS:
    d=day_table(t,e); T[e]=(d,make_paths(len(d)))
def job(a):
    p,e,m=a; d,paths=T[e]; pl=P[p]; row=pl['tabs']['regular']; res=[]
    for idx in paths:
        if m=='intra': res.append(sim_intra(d,idx,pl,row,gmin=sim2.GMIN))
        else:
            o,s=sim_path(d,idx,pl,row,m=='eod_on',gmin=sim2.GMIN); res.append((o,s,{}))
    return a,res
if __name__=='__main__':
    modes=('eod_off','eod_on','intra')
    jobs=[(p,e,m) for p in P for e in ERAS for m in modes]
    with Pool(4) as pool: R=dict(pool.map(job,jobs,chunksize=1))
    out={}
    for (p,e,m),res in R.items():
        out[f'{p}|{e}|{m}']=agg(res,len(res))
        if m=='intra':
            b=[r for r in res if r[0]=='bust' or (r[0]=='stuck')]
            kills=[r for r in res if r[0]=='bust']
            st=[r for r in res if r[0]=='stuck']
            out[f'{p}|{e}|intra']['mech']=dict(
                n_fail=len(b),n_kill=len(kills),n_stuck=len(st),
                kill_only_intraday=sum(1 for r in kills if r[2].get('only_intraday')),
                kill_raised_floor=sum(1 for r in kills if r[2].get('raised')),
                stuck_raised_floor=sum(1 for r in st if r[2].get('raised')))
            # path-level transitions vs EOD off
            ref=R[(p,e,'eod_off')]
            tr={}
            for a,b_ in zip(ref,res):
                k=('pass' if a[0]=='pass' else 'open' if a[0]=='open' else 'fail')+'>'+('pass' if b_[0]=='pass' else 'open' if b_[0]=='open' else 'fail')
                tr[k]=tr.get(k,0)+1
            out[f'{p}|{e}|intra']['trans']=tr
        if m=='eod_on':
            ref=R[(p,e,'eod_off')]
            out[f'{p}|{e}|eod_on']['path_identical']=sum(1 for a,b_ in zip(ref,res) if a[:2]==b_[:2])
    json.dump(out,open(HERE+f'/results{"" if ORD=="heur" else "_"+ORD}.json','w'),indent=1)
    print('done')
