import fsim, harness as H, numpy as np, time
for k in (50, 150):
    c = H.cfg(k, **H.BUILT[k]) if k in (50,150) else None
    t=time.time(); S, res, st = fsim.run(k, c, ds_frac=0.38, news=False, horizon=400)
    # eval-mode check
    c = S.mk(**c); days,_ = fsim.build_days(S, c, False)
    r = [fsim.life(S, k, days, i, c, 0.35, 0.38, 400, True) for i in range(S.L)]
    p = np.mean([x["status"]=="PASS" for x in r])*100
    print(k, "eval-mode pass%", round(p,1), "(expect 66.3 / 74.4)", st, round(time.time()-t))
