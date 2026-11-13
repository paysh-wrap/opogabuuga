import sys,os,json; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from multiprocessing import Pool
from sim2 import *
import sim2
P=load_plans(); t=load(); T={}
sim2.GMIN=smin(float(t[t.d>='2025-11-06'].entry.mean())); print('gmin',sim2.GMIN)
for e in ERAS:
    d=day_table(t,e); T[e]=(d,make_paths(len(d)))
def job(a):
    p,tab,e,m=a; d,paths=T[e]; return a,run_cfg(d,paths,P[p],P[p]['tabs'][tab],m=='on')
def sanity(a):
    p,e=a; d,paths=T[e]; pl=P[p]; row=dict(pl['tabs']['regular'],brake_below=None)
    return a,run_cfg(d,paths,pl,row,True,room=False,kill=0,margin=0,shrink=False)
if __name__=='__main__':
    jobs=[(p,tab,e,m) for p in P for tab in('regular','suggested','high') for e in ERAS for m in('on','off')]
    with Pool() as pool:
        res=pool.map(job,jobs,chunksize=4); san=pool.map(sanity,[('lucid_pro_25k','is'),('lucid_pro_25k','j'),('lucid_pro_25k','all')])
    out={'|'.join(a):r for a,r in res}; out['sanity']={'|'.join(a):r for a,r in san}
    json.dump(out,open('results.json','w'),indent=1)
    for k,v in out['sanity'].items(): print(k,{x:round(y) for x,y in v.items()})
