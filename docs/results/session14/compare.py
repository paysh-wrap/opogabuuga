"""Prints markdown comparison tables hindsight (old) vs causal (new) from session14/out/*/results_*.json."""
import json, os
D = os.path.dirname(os.path.abspath(__file__)) + "/out"
L = lambda r, f: json.load(open(f"{D}/{r}/{f}"))
H, C = "hindsight", "causal"


def e_cell(x):
    return f"{x['pass_']*100:.0f}/{x['bust']*100:.0f}/{x['frozen']*100:.0f} m{x['med']:.0f}"


print("### kill_study (D70 sizing, D71 kill distance): EVAL pass/bust/frozen % and median sessions; old -> new; all starts | 2021-23 | 2024-26\n")
print("| plan | kill | old all | new all | old 21-23 | new 21-23 | old 24-26 | new 24-26 |\n|---|---|---|---|---|---|---|---|")
h, c = L(H, "results_main.json"), L(C, "results_main.json")
for a, b in zip(h, c):
    if a["kind"] != "E":
        continue
    assert a["name"] == b["name"] and a["kill"] == b["kill"]
    print(f"| {a['name']} | {a['kill']} | " + " | ".join(f"{e_cell(a[k])} | {e_cell(b[k])}" for k in ("all", "e1", "e2")) + " |")
print("\n### kill_study FUNDED: mean income per 2 weeks $ (take/26), any payout %, frozen %; old -> new\n")
print("| plan | kill | old $/2wk | new $/2wk | old any-pay | new any-pay | old frozen | new frozen | old fade WR | new fade WR |\n|---|---|---|---|---|---|---|---|---|---|")
for a, b in zip(h, c):
    if a["kind"] != "F":
        continue
    x, y = a["all"], b["all"]
    print(f"| {a['name']} | {a['kill']} | {x['take']/26:.0f} | {y['take']/26:.0f} | {x['anypay']*100:.0f}% | {y['anypay']*100:.0f}% | {x['frozen']*100:.0f}% | {y['frozen']*100:.0f}% | {x['fade_wr']*100:.0f}% | {y['fade_wr']*100:.0f}% |")
print("\n### pm_fade_d57_study (D73: fade under D57 'tighten' vs live 'code'): EVAL pass/bust/frozen, old -> new (all | 21-23 | 24-26)\n")
print("| plan | fade mode | old all | new all | old 21-23 | new 21-23 | old 24-26 | new 24-26 |\n|---|---|---|---|---|---|---|---|")
h, c = L(H, "results_pm_fade.json"), L(C, "results_pm_fade.json")
for a, b in zip(h, c):
    if a["kind"] != "E":
        continue
    print(f"| {a['name']} | {a['fm']} | " + " | ".join(f"{e_cell(a[k])} | {e_cell(b[k])}" for k in ("all", "e1", "e2")) + " |")
print("\n### pm_fade FUNDED $/2wk and frozen %, old -> new\n")
print("| plan | fade mode | old $/2wk | new $/2wk | old frozen | new frozen |\n|---|---|---|---|---|---|")
for a, b in zip(h, c):
    if a["kind"] == "F":
        print(f"| {a['name']} | {a['fm']} | {a['all']['take']/26:.0f} | {b['all']['take']/26:.0f} | {a['all']['frozen']*100:.0f}% | {b['all']['frozen']*100:.0f}% |")
