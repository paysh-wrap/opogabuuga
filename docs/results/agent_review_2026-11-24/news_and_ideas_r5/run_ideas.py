import sys,pickle,numpy as np,pandas as pd
sys.path.insert(0,"/home/user/paytience/docs/results/agent_review_2026-11-24/model_qa_scripts")
from gen import *
L,_=pickle.load(open("/home/user/days.pkl","rb")); M=dict(L); days=[d for d,_ in L]
rng=np.random.default_rng(23)
FEE=2.0;SL=0.25;PV=2.0
def sim(d,k,side,stopd,entry=None,target=None):
    a=M[d]; e=a["open"][k]+side*SL if entry is None else entry
    stop=e-side*stopd; tp=None if target is None else e+side*target
    for j in range(k,390):
        h,l=a["high"][j],a["low"][j]
        if (side>0 and l<=stop) or (side<0 and h>=stop): return ((stop-e)*side)*PV-FEE,j
        if tp is not None and ((side>0 and h>=tp) or (side<0 and l<=tp)): return ((tp-e)*side)*PV-FEE,j
    return (a["close"][389]-e)*side*PV-FEE,389
def stats(p): p=np.asarray(p); return (len(p),round(pf(p),2) if len(p) else 0,round(p.sum()),round(p.mean(),1) if len(p) else 0)
def PJ(df): return df[df.d<"2024-01-01"],df[df.d>="2024-01-01"]
out=[]
# I1 ORB
def orb(nb,filt):
    R=[]
    for d in days:
        a=M[d]
        if not (d>="2021-10-21"): continue
        oh=a["high"][:nb].max(); ol=a["low"][:nb].min(); cd=np.sign(a["close"][nb-1]-a["open"][0])
        if cd==0: continue
        for k in range(nb,380):
            up=a["high"][k]>oh; dn=a["low"][k]<ol
            if up or dn:
                side=1 if up else -1
                if up and dn: break
                if filt and side!=cd: break
                e=(oh if side>0 else ol)+side*SL; sd=oh-ol if True else 0; sd=min(max(sd,4.0),60.0)
                # entry at the breakout level (stop order), simulate from bar k
                p,_=sim(d,k,side,sd,entry=e); R.append(dict(d=d,k=k,side=side,sd=sd,p=p)); break
    return pd.DataFrame(R)
ORB={"I1A_5m_filt":orb(5,True),"I1B_15m_filt":orb(15,True),"I1C_5m_nofilt":orb(5,False)}
def ctrl(df,win):
    x=df[df.d<"2024-01-01"] if win=="pick" else df[df.d>="2024-01-01"]
    res=[]
    for _ in range(2000):
        t=0;wins=[];
        ps=[]
        for r in x.itertuples():
            side=rng.choice([-1,1]); a=M[r.d]; ob=a["open"][r.k]
            p,_=sim(r.d,r.k,side,r.sd); ps.append(p)
        res.append((pf(ps),sum(ps)))
        if len(res)>=300: break  # cost control: 300 draws
    return np.array(res)
def report(name,df,sdcol=True):
    for w,x in zip(("pick","judge"),PJ(df)): out.append(f"{name:16s} {w:5s} n,PF,net,avg = {stats(x.p)}")
for k,v in ORB.items(): report(k,v)
# I3 valentini proxy
def val(thr):
    R=[]
    for d in days:
        if d<"2021-10-21": continue
        a=M[d]; rg=a["high"][:30].max()-a["low"][:30].min()
        if rg<=0: continue
        E_=abs(a["close"][29]-a["open"][0])/rg
        if E_<thr: continue
        side=1 if a["close"][29]>a["open"][0] else -1
        for k in range(30,120):
            v=a["vwap"][k]
            if (side>0 and a["low"][k]<=v and a["close"][k-1]>v) or (side<0 and a["high"][k]>=v and a["close"][k-1]<v):
                p,_=sim(d,k+1,side,40,entry=v+side*SL,target=60) if k+1<390 else (0,0)
                R.append(dict(d=d,k=k+1,side=side,sd=40,p=p)); break
    return pd.DataFrame(R)
VAL={"I3A_thr0.5":val(0.5),"I3B_thr0.35":val(0.35)}
for k,v in VAL.items(): report(k,v)
# controls for I1 and I3 judge (random direction)
def ctrl2(df,fn,n=300):
    x=df[df.d>="2024-01-01"]; res=[]
    for _ in range(n):
        ps=[]
        for r in x.itertuples():
            side=int(rng.choice([-1,1])); ps.append(fn(r,side))
        res.append((pf(ps),sum(ps)))
    return np.array(res)
for nm,df in ORB.items():
    c_=ctrl2(df,lambda r,s:sim(r.d,r.k,s,r.sd)[0]); j=df[df.d>="2024-01-01"]
    out.append(f"{nm} judge random-direction control: PF p95={np.percentile(c_[:,0],95):.2f} net p95={np.percentile(c_[:,1],95):.0f}; real PF={pf(j.p):.2f} net={j.p.sum():.0f}")
for nm,df in VAL.items():
    c_=ctrl2(df,lambda r,s:sim(r.d,r.k,s,40,entry=M[r.d]["vwap"][r.k-1]+s*SL,target=60)[0]); j=df[df.d>="2024-01-01"]
    out.append(f"{nm} judge random-direction control: PF p95={np.percentile(c_[:,0],95):.2f} net p95={np.percentile(c_[:,1],95):.0f}; real PF={pf(j.p):.2f} net={j.p.sum():.0f}")
# I2 daily bias on NOISE
nz=noise3.gen(); dh={d:M[d]["high"].max() for d in days}; dl={d:M[d]["low"].min() for d in days}; dc={d:M[d]["close"][389] for d in days}
idx={d:i for i,d in enumerate(days)}
def bias(d):
    i=idx[d]
    if i<2: return 0
    p1,p2=days[i-1],days[i-2]
    return 1 if dc[p1]>dh[p2] else (-1 if dc[p1]<dl[p2] else 0)
nz["bias"]=nz.d.map(bias); nz["aligned"]=nz.bias*nz.side
F={"I2F1_drop_counter":nz.aligned>=0 ,"I2F2_aligned_only":nz.aligned>0,"I2F3_counter_only":nz.aligned<0}
out.append("NOISE base counts by alignment: "+str(nz.aligned.value_counts().to_dict()))
for nm,m in F.items():
    for w,x in (("pick",nz[nz.d<"2024"]),("judge",nz[nz.d>="2024"])):
        keep=m[x.index]; kept=x[keep]; base=x.pnl.sum()
        # random control: keep same count at random
        nk=int(keep.sum()); up=[x.pnl.values[rng.choice(len(x),nk,replace=False)].sum() for _ in range(3000)]
        out.append(f"{nm:20s} {w:5s} kept n={nk}/{len(x)} PF {pf(kept.pnl):.2f} vs {pf(x.pnl):.2f}; net {kept.pnl.sum():.0f} vs {base:.0f}; rand-keep net p95={np.percentile(up,95):.0f}, p(rand>=real)={np.mean(np.array(up)>=kept.pnl.sum()):.3f}")
print("\n".join(out)); open("ideas_log.txt","w").write("\n".join(out))
