import os
H = os.path.dirname(os.path.abspath(__file__)); r = lambda f: open(f"{H}/{f}").read()
tb = r("RESULTS_tables.md"); parts = tb.split("### T1 ")
t0 = parts[0]; rest = "### T1 " + parts[1]
open(f"{H}/RESULTS.md", "w").write(r("RESULTS_head.md") + "## 3. Tables (all held-out unless the column says IS)\nColumns: HO = held-out 2024-01..2026-11; roll / boot / strict = Pro 25K eval simulations (see section 2); dNet = paired block-bootstrap 95% interval of net-profit difference vs the row's base; `yrs PF>=base` = calendar years (of 8, 2019 and 2026 partial) in which the variant's profit factor is >= its base's (all trades of the year).\n\n" + t0 + rest + "\n" + r("RESULTS_dow.md") + "\n" + r("RESULTS_extra.md") + r("RESULTS_tail.md"))
print("ok")
