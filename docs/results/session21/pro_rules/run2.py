import sys,os,json; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from multiprocessing import Pool
from sim2 import *
import sim2
P=load_plans(); t=load(); tf=load_fade(t); T={}; TF={}
sim2.GMIN=smin(float(t[t.d>='2025-11-06'].entry.mean())); print('gmin',sim2.GMIN)
for e in ERAS:
    d=day_table(t,e); T[e]=(d,make_paths(len(d)))
    TF[e]=day_table(tf,e)
def job(a):
    p,tab,e,m,fade=a; d,paths=T[e]
    if fade: d=TF[e]
    return a,run_cfg(d,paths,P[p],P[p]['tabs'][tab],m=='on')
if __name__=='__main__':
    jobs=[(p,tab,e,m,0) for p in P for tab in('regular','suggested','high') for e in ERAS for m in('on','off')]
    jobs+=[(p,'regular',e,m,1) for p in P for e in ERAS for m in('on','off')]
    with Pool() as pool: res=pool.map(job,jobs,chunksize=4)
    out={'|'.join(map(str,a)):r for a,r in res}
    json.dump(out,open('results.json','w'),indent=1)
    print(len(out), 'fade trades',len(tf)-len(t))
