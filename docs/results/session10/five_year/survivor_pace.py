import sys; sys.path.insert(0,'/home/user/opogabuuga/backend')
from decimal import Decimal as D
from pathlib import Path
from statistics import mean, median
from app.config import load_rules
from app.backtest.income_projection import rules_view, research_days, size_for, payout_amount, ZERO, CENT
H=260; STEP=2
PLANS={'25K':(1,None,10),'50K':(2,(D('.5'),1),10),'100K':(2,(D('.3'),1),5),'150K':(3,(D('.5'),2),5),'150K-High':(4,(D('.5'),2),5)}
def path(days,r,base,cad,brake,cap):
    bal=peak=r.start; floor=r.start-r.mll; cycle=[]; pays=[]; checks=[]; reach=None
    for n,trades in enumerate(days):
        day=ZERO; qty=base
        if brake and bal-floor<brake[0]*r.mll: qty=min(qty,brake[1])
        for p in trades:
            p*=qty
            if r.dll is not None and day+p<=-r.dll: p=-r.dll-day
            bal+=p; day+=p
            if bal<=floor: return dict(pays=pays,status='BUST',checks=checks,reach=reach)
            if r.dll is not None and day<=-r.dll: break
        if trades: cycle.append(day)
        if reach is None and bal>=r.buffer+r.min_request: reach=n+1
        peak=max(peak,bal); floor=r.lock_level if peak>=r.lock_trigger else max(floor,peak-r.mll)
        if (n+1)%cad==0 and (not cap or len(pays)<r.max_payouts):
            amt=payout_amount(r,bal,cycle,len(pays))
            if amt>0:
                checks.append((n+1,'PAID')); bal-=amt; pays.append((n+1,(amt*r.split).quantize(CENT))); cycle=[]
                floor=max(floor,r.lock_level)
            else:
                cp=sum(cycle,ZERO)
                if cp<r.min_cycle_profit or cp<=0: why='cycle profit below min'
                elif r.consistency_pct is not None and max(cycle)>r.consistency_pct/100*cp: why='consistency>40%'
                elif bal-r.buffer<=0: why='balance within buffer'
                else: why='below $500'
                checks.append((n+1,why))
        if cap and len(pays)>=r.max_payouts: return dict(pays=pays,status='MAXP',checks=checks,reach=reach)
    return dict(pays=pays,status='OPEN',checks=checks,reach=reach)
names,days=research_days(); days=list(days)
starts=list(range(0,len(days)-H,STEP))
def fm(x): return f'{float(x):,.0f}'
out=[]
def P(s=''): out.append(s)
P('# Payout pace study (agentL)\nCurrent live sizes (D64 Regular + brake; 150K-High = 4/2), cadence 25K/50K=10, 100K/150K=5 sessions, max-eligible, 90% split, 260-session horizon, starts every 2 sessions, per account (5 accounts take same trades => x5 for household). Data: main_strategy_5y.csv.\n')
for cap in (True,False):
  P(f'\n# {"WITH 5-payout cap (as live)" if cap else "NO payout cap (real pace)"}\n')
  for plan,(q,br,cad) in PLANS.items():
    f='150k' if plan.startswith('150K') else plan.lower()
    r=rules_view(load_rules(Path(f'/home/user/opogabuuga/config/rules/lucid_pro_{f}.yaml')).rules)
    if not cap: pass
    res=[(i,path(days[i:i+H],r,q,cad,br,cap)) for i in starts]
    P(f'\n## {plan} ({len(res)} starts; buffer {r.buffer}, min req {r.min_request}, caps {r.max_first}/{r.max_next}, cadence {cad})')
    for label,sel in (('ALL',lambda i:True),('H1 2021-11..2023-12',lambda i:names[i]<'2024-01'),('H2 2024-01..2026-10',lambda i:names[i]>='2024-01')):
      rs=[p for i,p in res if sel(i)]
      if not rs: continue
      def stats(rs,tag):
        n=len(rs)
        if n==0: return
        npay=[len(p['pays']) for p in rs]
        dist={k:sum(1 for x in npay if (x==k if k<5 else x>=5))/n*100 for k in range(6)}
        paid=[sum((a for _,a in p['pays']),ZERO) for p in rs]
        s=f'- {tag}: n={n} payouts/yr {mean(npay):.2f} | dist 0/1/2/3/4/5+ % = '+'/'.join(f'{dist[k]:.0f}' for k in range(6))+f' | mean paid ${fm(mean(paid))}'
        return s
      allrs=rs; bust=sum(1 for p in rs if p['status']=='BUST')/len(rs)*100
      P(f'\n**{label}** bust {bust:.1f}%')
      P(stats(allrs,'All'))
      sv=[p for p in rs if p['status']!='BUST']
      s=stats(sv,'Survivors')
      if s:
        fl=[p['pays'][0][0] for p in sv if p['pays']]
        s+=f' | median sess to 1st payout {median(fl) if fl else None}'
        P(s)
      # after first
      gaps=[];sizes=[];reasons={};tot=0;post=[]
      for p in rs:
        if not p['pays']: continue
        f1=p['pays'][0][0]
        ps=[n for n,_ in p['pays']]; gaps+=[b-a for a,b in zip(ps,ps[1:])]
        sizes+=[a for n,a in p['pays'][1:]]
        for n,w in p['checks']:
          if n>f1:
            tot+=1; reasons[w]=reasons.get(w,0)+1
      if gaps:
        P(f'- After 1st payout: gap sessions median {median(gaps)} mean {mean(gaps):.1f}; later-payout size to you mean ${fm(mean(sizes))} median ${fm(median(sizes))}; checks after 1st: {tot}; '+', '.join(f'{k} {v/tot*100:.0f}%' for k,v in sorted(reasons.items())))
      else: P('- After 1st payout: no consecutive payouts')
      need=r.buffer+r.min_request-r.start
      rc=[p['reach'] for p in rs if p['reach']]
      P(f'- Gross profit needed before 1st payout ${fm(need)}; reached by {len(rc)/len(rs)*100:.0f}% of starts; median session reached {median(rc) if rc else None} => remaining of 260: {H-median(rc) if rc else None}')
      ma=mean(paid:=[sum((a for _,a in p['pays']),ZERO) for p in rs]); ms=mean([sum((a for _,a in p['pays']),ZERO) for p in sv]) if sv else 0
      P(f'- $ per 2 weeks (10 sessions): 1 acct all ${float(ma)/26:,.0f}, survivors ${float(ms)/26:,.0f}; 5 accts all ${float(ma)*5/26:,.0f}, survivors ${float(ms)*5/26:,.0f}')
Path('report.md').write_text('\n'.join(out))
print('\n'.join(out))
