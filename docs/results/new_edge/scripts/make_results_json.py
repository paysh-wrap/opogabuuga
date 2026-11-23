import json, os
H = os.path.dirname(os.path.abspath(__file__))
a = json.load(open(H + "/leg_lastmom239.json")); b = json.load(open(H + "/leg_gapcont.json")); g = json.load(open(H + "/survivors_out.json"))
json.dump(dict(data="MNQ RTH 1-min 2021-10-21..2026-10-30 (no MGC / overnight data available in sandbox)", pick="2021-10..2023-12", judge="2024-01..2026-10",
               survivors_both_windows={k: dict(n_cfg=v["n_cfg"], n_survive=v["n_survive"]) for k, v in g.items()},
               late_day_momentum=a, gap_continuation=b), open(H + "/../results.json", "w"), indent=1)
