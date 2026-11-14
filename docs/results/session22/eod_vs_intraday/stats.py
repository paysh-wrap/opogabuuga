import sys,os,json; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import numpy as np, sim2
from sim2 import *
t=load(); pa=build_paths(t); mf=[];mp=[];pn=[]
for _,r in t.iterrows():
    u=pa[(r.d,int(r.ek))]; mf.append(u.max()); pn.append(r.pnl)
mf=np.array(mf); pn=np.array(pn); win=pn>0
o=dict(n=len(t),mean_mfe=mf.mean(),mean_pnl=pn.mean(),mean_giveback=(mf-pn).mean(),
  losers=int((~win).sum()),losers_with_mfe_ge100=int(((~win)&(mf>=100)).sum()),
  losers_with_mfe_ge250=int(((~win)&(mf>=250)).sum()),
  winners_giveback_mean=float((mf-pn)[win].mean()),
  share_trades_giveback_ge100=float(((mf-pn)>=100).mean()),
  sum_pnl=float(pn.sum()),sum_mfe=float(mf.sum()))
json.dump(o,open(os.path.dirname(os.path.abspath(__file__))+'/trade_stats.json','w'),indent=1); print(o)
