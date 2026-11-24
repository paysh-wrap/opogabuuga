import sys,os,time; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import pandas as pd, harness5 as H
H.LEG[0]=pd.read_csv("/home/user/paytience/docs/results/new_edge/late_leg_sizes/trades_app.csv")
for k,ng,gb in ((50,0,()),(50,2,((667,1),))):
    t=time.time();S=H.sim(k);c=H.cfg(k,**H.BUILT[k]);c["ng"]=ng;c["gbands"]=tuple((d/H.MLL[k],m) for d,m in gb)
    m=H.metrics(S,c);print(k,ng,{w:(round(m[w]["pass_"],1),m[w]["med"]) for w in("ALL","PICK","JUDGE")},round(m["profit"]),round(time.time()-t))
