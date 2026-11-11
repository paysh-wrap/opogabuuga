"""assembles RESULTS.md from results_*.json (+ the hand-written text in results_text.md pieces below). usage: python3 make_results.py"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import make_tables as T

ACCS = T.ACCS; ACCTS = T.ACCTS
SYM = {"YES": "**Y**", "SAFER, SLOWER": "s", "no": "-"}


def matrix(scen, base, era):
    sizing = json.load(open(f"{HERE}/results_{scen}.json"))["cfg"]["sizing"]
    _, v = T.delta_table(scen, sizing, base, era)
    rows = ["| account | AI 50% | AI 55% | AI 60% | AI 65% | AI 70% |", "|---|---|---|---|---|---|"]
    for a in ACCTS: rows.append(f"| Pro {a} | " + " | ".join(SYM[v[(a, c)]] for c in ACCS) + " |")
    return "\n".join(rows)


def have(s): return os.path.exists(f"{HERE}/results_{s}.json")


def build(text):
    o = [text["head"]]
    o.append("## Verdict matrix (split vs NOISE alone)\n\n**Y** = split better: bootstrap PASS up and BUST not up, and the 250-session rolling run not worse. **s** = safer but slower (BUST clearly lower, fewer evals finish inside 250 sessions). **-** = no better.\n")
    o.append("Held-out 2024-2026 (the judge), main scenario (Duo on MNQ + MGC), vs NOISE alone at the app's full size:\n\n" + matrix("main", "noise_full", "HO"))
    o.append("\nIn-sample 2019-2023 (where the call is picked), same comparison:\n\n" + matrix("main", "noise_full", "IS"))
    o.append("\nHeld-out, vs NOISE alone at half size (= 1 micro on every account here; isolates what the AI Duo half adds):\n\n" + matrix("main", "noise_half", "HO"))
    o.append(text["verdict"])
    sizing = "APP"
    o.append("## Held-out tables, main scenario (Duo on MNQ + MGC, hedge lock)\n\nHO = 2024-01 .. 2026-11. 'split' rows: mean over 40 seeds, [min..max] across seeds for net $ and PASS %. 'roll' = rolling-start eval, 250-session horizon, starts every 2nd session (a start whose eval is not finished = OPEN). 'boot' = 600 block-bootstrap paths (10-session blocks drawn from the held-out days), eval run to the end (up to 750 sessions). Trades / win % / net $ / max DD $ = a continuous account over the whole era (reset to the start balance after a bust), closed-trade drawdown. Median days = trading sessions.\n" + T.main_table("main", sizing, "HO"))
    o.append("\n### Split minus NOISE alone, held-out (percentage points, net $)\n\n*seeds better = share of the 40 AI seeds in which the bootstrap PASS is higher AND the bootstrap BUST is lower than NOISE alone.\n\n#### vs NOISE alone full size\n\n" + T.delta_table("main", sizing, "noise_full", "HO")[0])
    o.append("\n#### vs NOISE alone half size\n\n" + T.delta_table("main", sizing, "noise_half", "HO")[0])
    o.append("\n## In-sample (2019-2023) tables, main scenario\n" + T.main_table("main", sizing, "IS") + "\n\n#### In-sample delta vs NOISE alone full size\n\n" + T.delta_table("main", sizing, "noise_full", "IS")[0])
    o.append("\n## Sensitivities (held-out, delta vs NOISE alone full size)\n")
    for scen, title in (("mnq", "Duo on MNQ only (hedge lock vs NOISE is then the only interaction)"), ("strict", "'max 1 open position per account' (a Duo or NOISE entry that overlaps any open position is skipped; MNQ + MGC)"),
                        ("main_s15", "NOISE alone at the session-15 recommended sizes instead of the app default (25K 1, 50K 1, 100K 2 / 1, 150K 3 / 1 micros)")):
        if have(scen):
            sz = json.load(open(f"{HERE}/results_{scen}.json"))["cfg"]["sizing"]
            o.append(f"\n#### {title}\n\n" + T.delta_table(scen, sz, "noise_full", "HO")[0])
            o.append("\nVerdict matrix, held-out:\n\n" + matrix(scen, "noise_full", "HO") + "\n\nIn-sample:\n\n" + matrix(scen, "noise_full", "IS"))
    o.append(text["method"])
    return "\n".join(o)


if __name__ == "__main__":
    text = json.load(open(f"{HERE}/text_blocks.json"))
    open(f"{HERE}/RESULTS.md", "w").write(build(text))
    print("RESULTS.md written")
