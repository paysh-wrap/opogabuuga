import sys, io, contextlib, numpy as np, pandas as pd
R="/home/user/opogabuuga/docs/results"
sys.path.insert(0,R+"/tools"); sys.path.insert(0,R+"/session10")
import noise_area as NA, sim25k, one_year_compare as OC
CSV="/tmp/claude-0/-home-user-opogabuuga/528f0293-22e9-5e48-80a8-65343eb6ade7/scratchpad/data/mnq_5y.csv"
START,END="2021-11-01","2026-10-30"
class _P:
    def __init__(s,v): s.v=v
    def __mul__(s,e): return s.v
class Pts:
    def __init__(s,p): s.p=p
    def __bool__(s): return True
    def __rmul__(s,pos): return _P(pos*s.p)
days=NA.load_days(CSV)
nd=sum(1 for d,_ in days if START<=d<=END); nwk=nd/5
res={}
res["NOISE 1%"]=NA.run(days,14,60,0.01,3)
for usd in (250,120,100,80): res[f"NOISE ${usd}"]=NA.run(days,14,60,Pts((usd-2)/2),3)
for name,fn in (("OPEN_DRIVE",OC.open_drive),("ORB15",OC.orb15),("LHH",OC.lhh)):
    rows=[r for i in range(14,len(days)) if (r:=fn(days,i))]
    res[name]=pd.DataFrame(rows,columns=["d","side","entry","exit","pnl"])
def pf(p):
    l=-p[p<=0].sum(); return p[p>0].sum()/l if l else float("inf")
def st(t):
    if len(t)==0: return dict(n=0,win=0,avg=0,tot=0,pf=0,dd=0,worst=0)
    eq=t.pnl.cumsum(); return dict(n=len(t),win=(t.pnl>0).mean()*100,avg=t.pnl.mean(),tot=t.pnl.sum(),pf=pf(t.pnl),dd=(eq-eq.cummax()).min(),worst=t.pnl.min())
out=["# Agent A: MNQ 5y backtest (1 micro), 2021-11-01 -> 2026-10-30\n",
f"{nd} sessions ({nwk:.0f} weeks). Costs per noise_area/one_year_compare ($1 fee + 1 tick slip). Fixed-$ stop = (usd-2)/2 pts, applied via noise_area.run.\n"]
T={}
for k,t in res.items():
    t=t[(t.d>=START)&(t.d<=END)].copy(); T[k]=t; t.to_csv(f"trades_{k.replace(' ','_').replace('%','pct').replace('$','usd')}.csv",index=False)
out.append("## Overall\n\n| Strategy | trades | /wk | win% | $/trade | total $ | PF | maxDD $ | worst trade |\n|---|---|---|---|---|---|---|---|---|")
for k,t in T.items():
    s=st(t); out.append(f"| {k} | {s['n']} | {s['n']/nwk:.1f} | {s['win']:.1f} | {s['avg']:.2f} | {s['tot']:.0f} | {s['pf']:.2f} | {s['dd']:.0f} | {s['worst']:.0f} |")
out.append("\n## Halves\n\n| Strategy | H1 2021-11..2023-12 n / total $ / PF | H2 2024-01..2026-10 n / total $ / PF |\n|---|---|---|")
for k,t in T.items():
    a=st(t[t.d<"2024-01-01"]); b=st(t[t.d>="2024-01-01"])
    out.append(f"| {k} | {a['n']} / {a['tot']:.0f} / {a['pf']:.2f} | {b['n']} / {b['tot']:.0f} / {b['pf']:.2f} |")
out.append("\n## Per year (trades / total $ / PF; 2021 = Nov-Dec, 2026 = Jan-Oct). LOSING YEARS marked **LOSS**\n")
yrs=[2021,2022,2023,2024,2025,2026]
out.append("| Strategy | "+" | ".join(map(str,yrs))+" |\n|---|"+"---|"*len(yrs))
for k,t in T.items():
    cells=[]
    for y in yrs:
        g=t[pd.to_datetime(t.d).dt.year==y]; s=st(g)
        cells.append(f"{s['n']} / {s['tot']:.0f} / {s['pf']:.2f}"+(" **LOSS**" if s['tot']<0 else ""))
    out.append(f"| {k} | "+" | ".join(cells)+" |")
def simm(csv,start,end):
    r=sim25k.run("Pro",csv,q=1,dll_funded=600,start=start,end=end)
    n=len(r); ps=[x for x in r if x[0]=="pass"]; bs=sum(x[0]=="bust" for x in r)
    full=[x for x in ps if not x[4]]
    p1=sum(x[3]>=1 for x in full)/max(1,len(full)); ev=np.mean([x[2] for x in full]) if full else 0
    return dict(n=n,pass_=len(ps)/n*100,bust=bs/n*100,med=np.median([x[1] for x in ps]) if ps else float("nan"),p1=p1*100,ev=ev,val=ev*len(ps)/n)
def table(title,start,end):
    out.append(f"\n## {title}\n\n| Strategy | eval pass % | bust % | median eval days | >=1 payout % | avg paid $ | value/eval $ |\n|---|---|---|---|---|---|---|")
    for k in T:
        f=f"trades_{k.replace(' ','_').replace('%','pct').replace('$','usd')}.csv"
        m=simm(f,start,end); out.append(f"| {k} | {m['pass_']:.1f} | {m['bust']:.1f} | {m['med']:.0f} | {m['p1']:.1f} | {m['ev']:.0f} | {m['val']:.0f} |")
table("Pro 25K sim, full 5y (eval no DLL, funded DLL $600, 1 micro)",START,END)
table("Pro 25K sim, H1 2021-11..2023-12","2021-11-01","2023-12-31")
table("Pro 25K sim, H2 2024-01..2026-10","2024-01-01",END)
open("report.md","w").write("\n".join(out)+"\n"); print("\n".join(out))
