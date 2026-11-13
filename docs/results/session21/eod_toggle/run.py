import sys,os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import json,sys
from multiprocessing import Pool
from sim import *
n,f=load_streams(); nf=pd.concat([n,f])
P=load_plans(); T={}
for era in ERAS:
    for nm,df in(('base',n),('fade',nf)):
        d=day_table(df,era); T[(era,nm)]=(d,make_paths(len(d)))
def job(a):
    plan,tab,era,mode,stream=a
    d,paths=T[(era,stream)]
    return a,run_cfg(d,paths,P[plan],P[plan]['tabs'][tab],mode=='on')
def sanity(a):
    plan,tab,era,sz=a
    d=T[(era,'base')][0]; paths=make_paths(len(d),400,500); pl=dict(P[plan]); row=dict(pl['tabs'][tab]); row['contracts']=sz; row['brake_below']=None
    return a,run_cfg(d,paths,pl,row,True,room=False,kill=0,margin=0,maxs=500)
if __name__=='__main__':
    jobs=[(p,t,e,m,'base') for p in P for t in('regular','suggested','high') for e in ERAS for m in('on','off')]
    jobs+=[(p,'regular',e,m,'fade') for p in P for e in ERAS for m in('on','off')]
    with Pool() as pool:
        res=pool.map(job,jobs,chunksize=4)
        sj=[('lucid_pro_25k','regular','all',1),('lucid_pro_50k','regular','all',2),('lucid_pro_50k','regular','all',1)]
        san=pool.map(sanity,sj)
    out={'|'.join(map(str,a)):r for a,r in res}
    out['sanity']={'|'.join(map(str,a)):r for a,r in san}
    json.dump(out,open('results.json','w'),indent=1)
    print(out['sanity'])
