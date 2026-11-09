# Policy sim (bias_est.py-style). Inputs from D52/D53 engine stats, 1y. R: win +1.8R, loss -1R.
# with-day share 85% (STRATEGY_MAIN). Per market: (N, win_with, win_against)
M={"MNQ":(169,.35,.36),"MGC":(47,.39,.14)}
def ev(w): return w*2.0-(1-w)
def run(N,ww,wa,p,block_frac,sh=.85):
    nw,na=N*sh,N*(1-sh); base=nw*ev(ww)+na*ev(wa)
    # on blocked days (fraction block_frac): right p -> keep with, drop against; wrong -> drop with
    keep=(1-block_frac)*(nw*ev(ww)+na*ev(wa))+block_frac*(p*nw*ev(ww)+(1-p)*na*ev(wa)) \
         + 0  # (wrong days: with trades blocked, against kept)
    keep=(1-block_frac)*(nw*ev(ww)+na*ev(wa))+block_frac*(p*(nw*ev(ww))+(1-p)*(na*ev(wa)))
    trades=(1-block_frac)*N+block_frac*(p*nw+(1-p)*na)
    wins=(1-block_frac)*(nw*ww+na*wa)+block_frac*(p*nw*ww+(1-p)*na*wa)
    return base,keep,trades,wins/trades
def agree(p,rho=.5):  # two forecasters accuracy p, error correlation rho
    both_wrong=(1-p)**2+rho*p*(1-p); both_right=p*p+rho*p*(1-p)
    return both_right/(both_right+both_wrong), both_right+both_wrong
print("mkt acc | always-block dR win | strong-only(35%days) dR | agree(rho.5) acc_eff days dR")
for m,(N,ww,wa) in M.items():
  for p in (.5,.55,.6,.65):
    b,k,t,w=run(N,ww,wa,p,1); _,k2,t2,w2=run(N,ww,wa,p,.35)
    pa,fa=agree(p); _,k3,t3,w3=run(N,ww,wa,pa,fa*.6)
    print(f"{m} {p:.2f} | {k-b:+6.1f}R {t:5.0f}tr {w:.0%} | {k2-b:+6.1f}R {w2:.0%} | {pa:.2f} {fa*.6:.0%} {k3-b:+6.1f}R {t3:4.0f}tr {w3:.0%}")
  print(f"{m} base {b:+.1f}R {N}tr")
