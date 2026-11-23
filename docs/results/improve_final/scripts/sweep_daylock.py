import sys; sys.argv=['x']
sys.path.insert(0,"/home/user/opogabuuga/.claude/worktrees/agent-a9e55244751214135/docs/results/improve_final/scripts")
import improve as I, json
F=I.F; store=json.load(open(F.FN)); b=I.B
jobs=[]
for k in (25,50,100,150):
    for dl in (0.1,0.15,0.2,0.25,0.3):
        jobs.append((k,dict(sorted(dict(b[k],dlock=dl).items()))))
        for lk in (70,90): jobs.append((k,dict(sorted(dict(b[k],dlock=dl,lock=lk).items()))))
F.run(jobs,store)
for k in b:
    br=store[F.nm(k,dict(sorted(b[k].items())))]
    for key,r in store.items():
        if key.startswith(f"{k}|") and F.feas(k,r,br): print(k,key[2:],r["ALL"]["pass"],r["ALL"]["med"],r["JUDGE"]["pass"],r["PICK"]["pass"],r["profit"])
