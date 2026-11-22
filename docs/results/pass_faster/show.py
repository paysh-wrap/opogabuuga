import json, os
R = json.load(open(os.path.dirname(os.path.abspath(__file__)) + "/results.json"))
f = lambda x: "-" if x is None else f"{x:.0f}"
for meth in ("roll", "boot"):
    print("=====", meth)
    for k in (25, 50):
        for w in (("ALL", "PICK", "JUDGE") if meth == "roll" else ("ALL", "PICK", "JUDGE", "L12", "IS")):
            for m in ("BASE", "LOCK80", "N+CANDACE", "N+VWAP"):
                r = R[f"{m}|{k}|{meth}|{w}"]
                print(f"{k}K {w:6} {m:10} pass {r['pass_']:5.1f} bust {r['bust']:4.1f} stuck {r['stuck']:5.1f} run {r['run']:5.1f} med {f(r['med'])} p75 {f(r['p75'])} n={r['n']}")
print("===== static")
for k in (25, 50):
    for w in ("ALL", "PICK", "JUDGE"):
        for m in ("BASE", "LOCK80", "N+CANDACE", "N+VWAP"):
            r = R[f"{m}|{k}|static|{w}"]
            print(k, w, m, "t1", round(r["t1"]), "tp", round(r["tp"]), "dd1", round(r["dd1"]), "ddp", round(r["ddp"]), "taken", r["taken"], "skip", r["skip_open"], "size0", r["size0"], "sig", r["sig"])
