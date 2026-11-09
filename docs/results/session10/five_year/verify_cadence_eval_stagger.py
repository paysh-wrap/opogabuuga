import csv, datetime as dt, statistics as st
D='/home/user/opogabuuga/backend/app/backtest/data/main_strategy_5y.csv'
by={}
for r in csv.DictReader(l for l in open(D) if not l.startswith('#')): by.setdefault(r['d'],[]).append(float(r['pnl']))
a,b=dt.date.fromisoformat(min(by)),dt.date.fromisoformat(max(by))
days=[];d=a
while d<=b:
    if d.weekday()<5: days.append(by.get(d.isoformat(),[]))
    d+=dt.timedelta(1)
print(len(days),'sessions')
P={ # start,mll,trig,lock,fdll,edll,target,minreq,mincyc,mfirst,mnext, size,brake_below,brake_c
 '25k':(25000,1000,26100,25100,600,None,1250,500,250,1000,1500,1,None,None),
 '50k':(50000,2000,52100,50100,1200,1200,3000,500,500,2000,2500,2,.5,1),
 '100k':(100000,3000,103100,100100,1800,1800,6000,500,750,2500,3000,2,.3,1),
 '150k':(150000,4500,154600,150100,2700,2700,9000,500,1000,3000,3500,3,.5,2)}
BUF={'25k':26100,'50k':52100,'100k':103100,'150k':154600}
def run(seq,k,cad,qty=None,eval_=False,hz=None,brake=True):
    s,mll,trig,lock,fd,ed,tgt,mr,mc,m1,mn,sz,bb,bc=P[k]
    q0=sz if qty is None else qty
    dll=ed if eval_ else fd
    bal=peak=s; floor=s-mll; cyc=[]; paid=0.0; n_p=0; pos=0
    for n,tr in enumerate(seq):
        q=q0
        if brake and bb is not None and bal-floor<bb*mll: q=min(q,bc)
        day=0.0
        for p in tr:
            p*=q
            if dll is not None and day+p<=-dll: p=-dll-day
            bal+=p; day+=p
            if bal<=floor: return ('BUST',paid,n_p)
            if dll is not None and day<=-dll: break
        if tr:
            cyc.append(day)
            if day>0: pos+=1
        peak=max(peak,bal)
        floor=lock if peak>=trig else max(floor,peak-mll)
        if eval_:
            if bal-s>=tgt and pos>=1: return ('PASS',0,n+1)
            continue
        if (n+1)%cad==0:
            cp=sum(cyc)
            if cp>=mc and cp>0 and max(cyc)<=0.4*cp:
                amt=min(bal-BUF[k],m1 if n_p==0 else mn)
                if amt>=mr:
                    amt=round(amt,2); bal-=amt; paid+=round(amt*.9,2); n_p+=1; cyc=[]
                    if n_p>=5: return ('MAX',paid,n_p)
    return ('OPEN',paid,n_p)
N=len(days)
def funded(k,cad,qty=None):
    r=[run(days[i:i+260],k,cad,qty) for i in range(0,N-260,2)]
    return r
out=[]
def pr(*a):
    s=' '.join(str(x) for x in a); print(s,flush=True); out.append(s)
pr('## A: 5-acct per-2-week equiv, bust%')
for k in P:
    row=[]
    for cad in (3,10):
        r=funded(k,cad); mean=st.mean(x[1] for x in r)*5
        row.append(f"cad{cad}: ${mean/26:,.0f} bust {100*sum(x[0]=='BUST' for x in r)/len(r):.1f}% (yr ${mean:,.0f})")
    pr(k,*row)
pr('## 3: value per eval')
for k,hz in (('25k',120),('50k',120),('100k',250),('150k',250)):
    paid=st.mean(x[1] for x in funded(k,10))
    for eq in range(1,max(P[k][11]+3,3)+1):
        for br in (False,True):
            er=[run(days[i:i+hz],k,10,eq,True,brake=br) for i in range(0,N-hz-10,2)]
            pp=sum(x[0]=='PASS' for x in er)/len(er)
            pr(k,'evalq',eq,'evalbrake' if br else 'evalNObrake',f'pass {pp:.1%} funded ${paid:,.0f} value ${pp*paid:,.0f}')
pr('## 4: stagger (5 accts)')
def stag(k,gap,lo_hi=None):
    offs=[j*gap for j in range(5)]
    tot=[];ab=0
    rng=range(0,N-260-offs[-1],2)
    for i in rng:
        rs=[run(days[i+o:i+o+260],k,10) for o in offs]
        tot.append(sum(x[1] for x in rs)); ab+=all(x[0]=='BUST' for x in rs)
    s=sorted(tot)
    return st.mean(tot),sum(t==0 for t in tot)/len(tot),ab/len(tot),s[int(.25*(len(s)-1)+.5)],len(tot)
for k in ('50k','100k','150k'):
    for gap in (0,21,42):
        m,z,ab,p25,n=stag(k,gap)
        pr(k,'gap',gap,f'mean ${m:,.0f} P0 {z:.1%} allbust {ab:.1%} p25 ${p25:,.0f} n={n}')
# artifact check: same-day restricted to starts range of gap-42 (i < N-260-168)
for k in ('150k',):
    for gap in (0,42):
        offs=[j*gap for j in range(5)]
        lim=N-260-168
        tot=[];ab=0
        for i in range(0,lim,2):
            rs=[run(days[i+o:i+o+260],k,10) for o in offs]
            tot.append(sum(x[1] for x in rs)); ab+=all(x[0]=='BUST' for x in rs)
        pr(k,'restricted window gap',gap,f'mean ${st.mean(tot):,.0f} P0 {sum(t==0 for t in tot)/len(tot):.1%} allbust {ab/len(tot):.1%} n={len(tot)}')
open('results.txt','w').write('\n'.join(out))
