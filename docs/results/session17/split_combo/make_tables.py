"""results_*.json -> tables (markdown fragments written to tables_<scenario>.md and printed). usage: python3 make_tables.py"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ACCTS = ["25K", "50K", "100K", "150K"]; ACCS = ["0.5", "0.55", "0.6", "0.65", "0.7"]
B = json.load(open(f"{HERE}/results_baselines.json"))


def g(d, k): return d[k]["mean"] if isinstance(d[k], dict) else d[k]
def f0(x): return "-" if x != x else f"{x:,.0f}"
def f1(x): return "-" if x != x else f"{x:,.1f}"
def rng(d, k, f=f0): return f"{f(d[k]['mean'])} [{f(d[k]['min'])}..{f(d[k]['max'])}]"


def flat(d, pre=""):
    for k, v in d.items():
        if isinstance(v, dict): yield from flat(v, f"{pre}{k}.")
        else: yield f"{pre}{k}", v


def base_row(b, era):
    d = dict(flat(b[era]))
    return {k: v for k, v in d.items()}


def main_table(scen, sizing, era="HO"):
    R = json.load(open(f"{HERE}/results_{scen}.json")); res = R["res"]; out = []
    for acct in ACCTS:
        bb = B[f"{sizing}|{acct}"]
        out.append(f"\n**Pro {acct}**\n")
        out.append("| setup | trades | win % | net $ | max DD $ | roll PASS % | roll BUST % | roll OPEN % | roll med days | boot PASS % | boot BUST % | boot med days |")
        out.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
        for nm, key in (("NOISE alone, full size", "noise_full"), ("NOISE alone, half size (diagnostic)", "noise_half")):
            d = dict(flat(bb[key][era])); 
            out.append(f"| {nm} | {f0(d['stream.n'])} | {f1(d['stream.win'])} | {f0(d['stream.net'])} | {f0(d['stream.dd'])} | {f0(d['roll.pas'])} | {f0(d['roll.bust'])} | {f0(d['roll.open'])} | {f0(d['roll.med_days'])} | {f0(d['boot.pas'])} | {f0(d['boot.bust'])} | {f0(d['boot.med_days'])} |")
        for acc in ACCS:
            d = res[acct][acc]; p = era + "."
            out.append(f"| **split, AI {int(float(acc)*100)}%** | {f0(g(d, p+'stream.n'))} | {f1(g(d, p+'stream.win'))} | {rng(d, p+'stream.net')} | {f0(g(d, p+'stream.dd'))} | {rng(d, p+'roll.pas')} | {f0(g(d, p+'roll.bust'))} | {f0(g(d, p+'roll.open'))} | {f0(g(d, p+'roll.med_days'))} | {rng(d, p+'boot.pas')} | {f0(g(d, p+'boot.bust'))} | {f0(g(d, p+'boot.med_days'))} |")
    return "\n".join(out)


def delta_table(scen, sizing, base="noise_full", era="HO"):
    """split minus NOISE alone, in percentage points: rolling PASS / BUST and bootstrap PASS / BUST, + net $"""
    R = json.load(open(f"{HERE}/results_{scen}.json"))["res"]; out = ["| account | AI acc | roll PASS d | roll BUST d | boot PASS d | boot BUST d | net $ d | seeds better* | beats? |", "|---|---|---|---|---|---|---|---|---|"]
    verdict = {}
    for acct in ACCTS:
        bb = dict(flat(B[f"{sizing}|{acct}"][base][era]))
        for acc in ACCS:
            d = R[acct][acc]; p = era + "."
            dp, db = g(d, p + "roll.pas") - bb["roll.pas"], g(d, p + "roll.bust") - bb["roll.bust"]
            bp, bbu = g(d, p + "boot.pas") - bb["boot.pas"], g(d, p + "boot.bust") - bb["boot.bust"]
            dn = g(d, p + "stream.net") - bb["stream.net"]
            # YES = bootstrap PASS up and BUST not up, and the 250-session rolling run is not worse (pass >= -1 pp, bust <= +1 pp)
            # SAFER-SLOWER = bust clearly lower in the bootstrap and not higher rolling, but fewer evals finish inside 250 sessions
            if bp > 1 and bbu <= 1 and db <= 1 and dp >= -1: ok = "YES"
            elif bbu < -1 and db <= 1 and dp < -1: ok = "SAFER, SLOWER"
            else: ok = "no"
            verdict[(acct, acc)] = ok
            fr = "-"
            if "vals" in d[p + "boot.pas"]:
                bs = list(zip(d[p + "boot.pas"]["vals"], d[p + "boot.bust"]["vals"]))
                fr = f"{100 * sum(1 for a_, b_ in bs if a_ > bb['boot.pas'] and b_ < bb['boot.bust']) / len(bs):.0f}%"
            out.append(f"| {acct} | {int(float(acc)*100)}% | {dp:+.0f} | {db:+.0f} | {bp:+.0f} | {bbu:+.0f} | {dn:+,.0f} | {fr} | {ok} |")
    return "\n".join(out), verdict


if __name__ == "__main__":
    for scen in [s for s in ("main", "mnq", "strict", "mnq_strict", "main_s15", "mnq_s15") if os.path.exists(f"{HERE}/results_{s}.json")]:
        sizing = json.load(open(f"{HERE}/results_{scen}.json"))["cfg"]["sizing"]
        with open(f"{HERE}/tables_{scen}.md", "w") as fh:
            for era in ("HO", "IS"):
                fh.write(f"\n### {scen} - {era} - split vs NOISE alone full size\n\n" + main_table(scen, sizing, era) + "\n")
                for base in ("noise_full", "noise_half"):
                    t, _ = delta_table(scen, sizing, base, era); fh.write(f"\n#### {scen} {era} delta vs {base}\n\n" + t + "\n")
        print("wrote", scen)
