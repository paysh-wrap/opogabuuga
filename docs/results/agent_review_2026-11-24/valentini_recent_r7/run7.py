import sys,pickle,json,numpy as np,pandas as pd
sys.path.insert(0,"/home/user/paytience/docs/results/agent_review_2026-11-24/model_qa_scripts")
sys.path.insert(0,"."); 
from gen import *
import h7 as H
L,_=pickle.load(open("/home/user/days.pkl","rb")); M=dict(L); days=[d for d,_ in L]
rng=np.random.default_rng(77); FEE=2.0;SL=0.25;PV=2.0
def sim(d,k,side,sd,entry,tgt):
    a=M[d]; e=entry; stop=e-side*sd; tp=e+side*tgt
    for j in range(k,390):
        h,l=a["high"][j],a["low"][j]
        if (side>0 and l<=stop) or (side<0 and h>=stop): return -sd*PV-FEE,j
        if (side>0 and h>=tp) or (side<0 and l<=tp): return tgt*PV-FEE,j
    return (a["close"][389]-e)*side*PV-FEE,389
def val(thr,sd,tg):  # same definition as news_and_ideas_r5 run_ideas.py (stop/target made parameters)
    R=[]
    for d in days:
        if d<"2021-10-21": continue
        a=M[d]; rg=a["high"][:30].max()-a["low"][:30].min()
        if rg<=0 or abs(a["close"][29]-a["open"][0])/rg<thr: continue
        side=1 if a["close"][29]>a["open"][0] else -1
        for k in range(30,120):
            v=a["vwap"][k]
            if (side>0 and a["low"][k]<=v and a["close"][k-1]>v) or (side<0 and a["high"][k]>=v and a["close"][k-1]<v):
                if k+1<390:
                    e=v+side*SL; p,j=sim(d,k+1,side,sd,e,tg); R.append(dict(d=d,ek=k+1,xk=j,side=side,stop=sd,tgt=tg,e=e,p=p,pts=(p+FEE)/PV))
                break
    return pd.DataFrame(R)
V=[(t,s,g) for t in (0.35,0.5) for s,g in ((40,60),(30,45),(60,90))]; assert len(V)==6
A=("2024-01-01","2025-06-30");B=("2025-07-01","2026-10-31")
def w(df,lo,hi): return df[(df.d>=lo)&(df.d<=hi)]
out=[];D={v:val(*v) for v in V}
out.append("variants (thr,stop,target): pick-part 2024-01..2025-06 PF/net/n")
best=None
for v in V:
    x=w(D[v],*A); out.append(f"{v} n={len(x)} PF={pf(x.p):.2f} net={x.p.sum():.0f}")
    if len(x)>=40 and (best is None or pf(x.p)>best[0]): best=(pf(x.p),v)
v=best[1]; out.append(f"FROZEN (best recent-pick PF): {v}"); df=D[v]
def block(x,lab):
    p=x.p.values; cum=np.cumsum(p); dd=(np.maximum.accumulate(np.r_[0,cum])[1:]-cum).max() if len(p) else 0
    return f"{lab:22s} n={len(p)} win={100*(p>0).mean() if len(p) else 0:.1f}% PF={pf(p):.2f} net={p.sum():.0f} maxDD={dd:.0f}"
for lab,lo,hi in (("pre-2024","2000","2023-12-31"),("recent-pick 24-01..25-06",*A),("recent-JUDGE 25-07..26-10",*B),("full 2024-26","2024-01-01","2026-12-31")): out.append(block(w(df,lo,hi),lab))
df["hy"]=[d[:4]+("H1" if int(d[5:7])<=6 else "H2") for d in df.d]
for h,x in df.groupby("hy"): out.append(f"  {h}: n={len(x)} PF={pf(x.p):.2f} net={x.p.sum():.0f}")
# random-direction control on judge
j=w(df,*B); res=[]
for _ in range(1000):
    ps=[sim(r.d,r.ek,s,r.stop,r.e if s==r.side else M[r.d]["vwap"][r.ek-1]+s*SL,r.tgt)[0] for r in j.itertuples() for s in [int(rng.choice([-1,1]))]]
    res.append((pf(ps),sum(ps)))
res=np.array(res); out.append(f"judge random-direction control (1000): PF p95={np.percentile(res[:,0],95):.2f} net p95={np.percentile(res[:,1],95):.0f}; real PF={pf(j.p):.2f} net={j.p.sum():.0f}")
# correlation with NOISE+CANDACE daily P&L (1 micro each)
nz=noise3.gen(); cd=pd.read_csv("/home/user/paytience/docs/results/pass_faster_c125/streams_candace_base.csv")
cd["pnl"]=cd.p1*2-2
dn=nz.groupby("d").pnl.sum(); dc=cd.groupby("day").pnl.sum(); dp=df.groupby("d").p.sum()
idx=pd.Index(days); ds=pd.DataFrame({"nc":dn.add(dc,fill_value=0).reindex(idx).fillna(0),"p":dp.reindex(idx).fillna(0)})
for lab,lo,hi in (("full","2021-10-21","2026-12"),("recent 24-26","2024-01-01","2026-12"),("judge","2025-07-01","2026-12")):
    x=ds[(ds.index>=lo)&(ds.index<=hi)]; out.append(f"corr daily P&L proxy vs NOISE+CANDACE {lab}: {x.corr().iloc[0,1]:.3f} (all days); on days proxy traded: {x[x.p!=0].corr().iloc[0,1]:.3f}")
print("\n".join(out),flush=True)
# fast-pass sim
H.PLANS; res_s={}
for K in (50,150):
    S=H.sim(K); S.PROXY=df[["d","ek","xk","pts","stop"]]
    for tag,pr in (("base",0),("+proxy",1)):
        c=H.cfg(K,**H.BUILT[K]); c["pr"]=pr
        mk=S.mk(**c); days_=S.build_days(mk); r=S.roll(mk,days_); st=S.static(mk,days_)
        o,n=r["out"],r["ses"]; ix=lambda lo:[i for i,d in enumerate(S.DATES) if d>=lo]
        row={}
        for nm,lo in (("all","2021-10-21"),("2024+","2024-01-01"),("2025-07+","2025-07-01")):
            i=np.array(ix(lo)); oo=o[i];nn=n[i];p=oo==0
            row[nm]=(round(100*p.mean(),1),float(np.median(nn[p])) if p.any() else None,round(100*((oo==1)|(oo==3)).mean(),1))
        row["profit"]=round(st["profit"]);row["dd"]=round(st["dd"]); res_s[f"{K}_{tag}"]=row
        line=f"SIM {K}K {tag}: {row}"; print(line,flush=True); out.append(line)
open("run7.log","w").write("\n".join(out))
