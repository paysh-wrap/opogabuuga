import json, sys
v = json.load(open("study.json"))["variants"]
print(f'{"name":52s} | IS n win pf net  | HO n  win  avg   net   dd   pf | roll P/B med | boot P/B med | strict P/B')
for n, r in v.items():
    i, h = r["IS"], r["HO"]
    print(f'{n[:52]:52s} | {i["n"]:4d} {i["win"]:4.1f} {i["pf"]:4.2f} {i["net"]:6.0f} {i["ratio"]:4.2f} | {h["n"]:4d} {h["win"]:4.1f} {h["avg"]:5.1f} {h["net"]:6.0f} {h["dd"]:5.0f} {h["pf"]:4.2f} | {h["roll"]["pass_"]:4.1f}/{h["roll"]["bust"]:4.1f} {h["roll"]["med"]:3.0f} | {h["boot"]["pass_"]:4.1f}/{h["boot"]["bust"]:4.1f} {h["boot"]["med"]:3.0f} | {h["roll_strict"]["pass_"]:4.1f}/{h["roll_strict"]["bust"]:4.1f}')
