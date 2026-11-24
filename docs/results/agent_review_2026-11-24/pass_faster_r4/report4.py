import json; R = json.load(open("results4.json")); FL = {25: 62, 50: 62, 100: 70, 150: 70}
print("| plan | variant | pick pass/med | judge pass/med | all pass/med | stuck+bust | profit | +$2 all/judge | HY min/med/max | candidate |"); print("|"+"---|"*10)
for key, r in R.items():
    k, n = key.split("|"); k = int(k); b = R[f"{k}|BUILT"]; m, c = r["base"], r["c2"]
    f = lambda w: f'{m[w]["pass_"]:.1f}/{m[w]["med"]:g}'
    ok = n != "BUILT" and all(m[w]["pass_"] > b["base"][w]["pass_"] and m[w]["med"] < b["base"][w]["med"] for w in ("PICK", "JUDGE")) \
        and m["profit"] >= b["base"]["profit"] and m["ALL"]["pass_"] >= min(FL[k], b["base"]["ALL"]["pass_"]) \
        and c["ALL"]["pass_"] >= b["c2"]["ALL"]["pass_"] and m["hy_min"] >= b["base"]["hy_min"]
    print(f'| {k}K | {n} | {f("PICK")} | {f("JUDGE")} | {f("ALL")} | {m["ALL"]["stuck_bust"]:.1f} | {m["profit"]:.0f} | {c["ALL"]["pass_"]:.1f}/{c["JUDGE"]["pass_"]:.1f} | {m["hy_min"]:.0f}/{m["hy_med"]:.0f}/{m["hy_max"]:.0f} | {"YES" if ok else ("-" if n=="BUILT" else "no")} |')
