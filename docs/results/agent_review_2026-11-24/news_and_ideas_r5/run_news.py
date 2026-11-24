import sys,pickle,datetime as dt,json
sys.path.insert(0,"/home/user/paytience/docs/results/agent_review_2026-11-24/model_qa_scripts")
from gen import *
import pandas as pd,numpy as np
L,_=pickle.load(open("/home/user/days.pkl","rb")); M=dict(L); dates=[d for d,_ in L]
ev=pd.read_csv("dates_us_releases.csv")
def off(t): h,m=map(int,t.split(':')); return h*60+m-570
ev["off"]=ev.time_et.map(off)
byday={d:g for d,g in ev.groupby("date")}
# ISM approx (UNSOURCED): 1st and 3rd trading day of month at 10:00
s=pd.Series(pd.to_datetime(dates)); ism=set()
for m,g in s.groupby(s.dt.strftime("%Y-%m")):
    g=sorted(g); ism.add(g[0].strftime("%Y-%m-%d"))
    if len(g)>2: ism.add(g[2].strftime("%Y-%m-%d"))
def evoffs(d,approx=False):
    o=[] if d not in byday else list(byday[d].off)
    if approx and d in ism: o.append(30)
    return o
PK=lambda x,col:x[x[col]<"2024-01-01"]; JG=lambda x,col:x[x[col]>="2024-01-01"]
# streams
nz=noise3.gen(); nz["day"]=nz.d; nz["ent"]=nz.ek; nz["ext"]=nz.xk; nz["usd"]=nz.pnl
c=pd.read_csv("/home/user/paytience/docs/results/pass_faster_c125/streams_candace_base.csv"); c["usd"]=c.p1*2-2; c["ent"]=c.idx.astype(int); c["ext"]=c.exit_idx.astype(int)
c["sgn"]=np.where(c.dir=="LONG",1,-1); c["entpx"]=c.entry
la=pd.read_csv("/home/user/paytience/docs/results/new_edge/late_leg_sizes/trades_app.csv"); la["day"]=la.day; la["usd"]=la.pts*2-2; la["ent"]=la.idx; la["ext"]=la.exit_idx; la["sgn"]=la.side
def entpx_noise(r): return M[r.day]["open"][r.ent]+r.side*0.25
def apply(t,strategy,pre,post,flat_off,approx=False):
    """pre/post: entry-block minutes before/after event; flat_off: minutes before event to flatten (positions open). returns new df, with status."""
    out=[];st=[]
    for r in t.itertuples():
        o=evoffs(r.day,approx); status="ok"; p=r.usd
        if any(e-pre<=r.ent<=e+post for e in o): out.append(np.nan); st.append("blocked"); continue
        cut=[e-flat_off for e in o if e-flat_off>r.ent and r.ext>=e-flat_off]
        if cut:
            Tf=min(cut); a=M[r.day]; px=a["close"][Tf-1]
            if strategy=="NOISE": e0=r.entpx_; p=(px-r.side*0.25-e0)*r.side*2-1
            else: p=(px-r.entry_)*r.sgn*2-2 if strategy=="CAND" else (px-a["open"][r.ent])*r.sgn*2-2
            status="cut"
        out.append(p); st.append(status)
    t=t.copy(); t["new"]=out; t["status"]=st; return t
nz["entpx_"]=[M[r.day]["open"][r.ent]+r.side*0.25 for r in nz.itertuples()]
nz["entry_"]=nz.entpx_; c["entry_"]=c.entry; la["entry_"]=[M[r.day]["open"][r.ent] for r in la.itertuples()]
S={"NOISE":nz,"CANDACE":c,"LATE":la}
key={"NOISE":"NOISE","CANDACE":"CAND","LATE":"LATE"}
def summ(p):
    p=np.asarray(p,float); p=p[~np.isnan(p)]
    return len(p),(100*(p>0).mean() if len(p) else 0),pf(p) if len(p) else 0,(p.mean() if len(p) else 0),p.sum()
lines=[]
def L_(s): print(s); lines.append(s)
# validate reproduction
L_("## repro: NOISE n=%d net=%.0f (expect 654 / 19293); CANDACE n=%d net=%.0f; LATE n=%d net=%.0f"%(len(nz),nz.usd.sum(),len(c),c.usd.sum(),len(la),la.usd.sum()))
# ---- Part a
cls={"FOMC_DECISION":lambda d:d in byday and (byday[d].event=="FOMC_DECISION").any(),"FOMC_MINUTES":lambda d:d in byday and (byday[d].event=="FOMC_MINUTES").any()}
for e in ["CPI","PPI","NFP","JOLTS","GDP"]: cls[e]=(lambda e:lambda d:d in byday and (byday[d].event==e).any())(e)
cls["ANY_EVENT"]=lambda d:d in byday; cls["NO_EVENT"]=lambda d:d not in byday
cls["KEY3(FOMC,CPI,NFP)"]=lambda d:d in byday and byday[d].event.isin(["FOMC_DECISION","CPI","NFP"]).any()
rng=np.random.default_rng(11)
A=[]
for sn,t in S.items():
    for win,f in (("pick",PK),("judge",JG),("all",lambda x,col:x)):
        tt=f(t,"day"); 
        for k,fn in cls.items():
            m=tt.day.map(fn).values; x=tt.usd.values[m]
            if len(x)==0: continue
            n,w,pfv,av,net=summ(x)
            rest=tt.usd.values[~tt.day.map(cls["NO_EVENT"] if k!="NO_EVENT" else cls["ANY_EVENT"]).values]
            pv=np.nan
            if k not in("NO_EVENT",) and len(x)>=5:
                ne=tt.usd.values[tt.day.map(cls["NO_EVENT"]).values]; diff=x.mean()-ne.mean(); allv=np.concatenate([x,ne]); cnt=0
                for _ in range(5000):
                    rng.shuffle(allv); cnt+=abs(allv[:len(x)].mean()-allv[len(x):].mean())>=abs(diff)
                pv=cnt/5000
            A.append(dict(strategy=sn,window=win,cls=k,n=n,win_pct=round(w,1),PF=round(pfv,2),avg=round(av,2),net=round(net),p_vs_noevent=pv))
pd.DataFrame(A).to_csv("part_a_event_days.csv",index=False)
# ---- Part b
B=[]
scen={"APP_INTERNAL":(15,1,2),"HARD_BREACH_ONLY":(1,1,1)}
for sc,(pre,post,fl) in scen.items():
  for approx in (False,True):
    for sn,t in S.items():
        r=apply(t,key[sn],pre,post,fl,approx)
        for win,f in (("pick",PK),("judge",JG),("all",lambda x,col:x)):
            tt=f(r,"day"); base=tt.usd.sum(); n0=len(tt)
            nb=(tt.status=="blocked").sum(); nc=(tt.status=="cut").sum()
            n,w,pfv,av,net=summ(tt.new)
            bp=pf(tt.usd.values)
            B.append(dict(scenario=sc+("+ISMapprox" if approx else ""),strategy=sn,window=win,base_n=n0,base_net=round(base),base_PF=round(bp,2),blocked=nb,cut_short=nc,new_n=n,new_net=round(net),new_PF=round(pfv,2),d_net=round(net-base),d_pct=round(100*(net-base)/base,1) if base else 0,
                       blocked_net_lost=round(tt.usd[tt.status=="blocked"].sum()),cut_orig_net=round(tt.usd[tt.status=="cut"].sum()),cut_new_net=round(tt.new[tt.status=="cut"].sum())))
pd.DataFrame(B).to_csv("part_b_news_rules.csv",index=False)
# ---- Part c
union=lambda d:cls["KEY3(FOMC,CPI,NFP)"](d)
V={"V1_skip_FOMC":(cls["FOMC_DECISION"],0),"V2_skip_CPI":(cls["CPI"],0),"V3_skip_NFP":(cls["NFP"],0),"V4_skip_union":(union,0),"V5_halve_union":(union,.5),"V6_halve_FOMC":(cls["FOMC_DECISION"],.5)}
def var(t,fn,mult):
    m=t.day.map(fn).values; return np.where(m,t.usd.values*mult,t.usd.values),m
C=[]
for name,(fn,mult) in V.items():
    row=dict(variant=name)
    for win,f in (("pick",PK),("judge",JG)):
        tt=f(nz,"day"); nu,m=var(tt,fn,mult); base=tt.usd.values
        row[win+"_n_days_hit"]=tt.day[m].nunique(); row[win+"_trades_hit"]=int(m.sum())
        row[win+"_base_net"]=round(base.sum()); row[win+"_new_net"]=round(nu.sum()); row[win+"_uplift"]=round(nu.sum()-base.sum())
        row[win+"_PF_base"]=round(pf(base),2); row[win+"_PF_new"]=round(pf(nu),2)
        # random control: same number of event days, drawn at random from window days w/ trades
        ud=tt.day.unique(); k=tt.day[m].nunique(); up=[]
        dpnl=tt.groupby("day").usd.sum()
        for _ in range(5000):
            pick=rng.choice(ud,k,replace=False); up.append(-(1-mult)*dpnl[pick].sum())
        row[win+"_rand_p95"]=round(np.percentile(up,95)); row[win+"_p_rand"]=round(np.mean(np.array(up)>=nu.sum()-base.sum()),3)
    row["pass"]=bool(row["pick_uplift"]>=0 and row["judge_uplift"]>=0 and row["judge_PF_new"]>row["judge_PF_base"] and row["judge_uplift"]>row["judge_rand_p95"])
    C.append(row)
pd.DataFrame(C).to_csv("part_c_noise_skip_halve.csv",index=False)
L_("\nPART B\n"+pd.DataFrame(B)[pd.DataFrame(B).window!="all"].to_string())
L_("\nPART C\n"+pd.DataFrame(C).T.to_string())
L_("\nPART A (NOISE/CAND/LATE, class rows)\n"+pd.DataFrame(A).to_string())
open("run_news.log","w").write("\n".join(lines))
