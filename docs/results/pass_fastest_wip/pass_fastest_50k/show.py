"""Quick printing helpers for the store (not part of the deliverable logic)."""
import sys, os, pickle, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def desc(c):
    s = f"s{c['stop']} n{c['nn']}"
    if c["grow"]: s += f" g{int(c['grow'])}/{c['gmax']}"
    if c["bb"]: s += f" b{c['bb']:g}"
    if c["tb"]: s += f" t{c['tb']:g}"
    if c["dl"]: s += f" dl{c['dl']:g}"
    s += f" m{c['mx']} L{c['trig']} {'MON' if c['mon'] else 'nomon'}"
    if c["fade"]: s += " FADE" + ("(sh)" if c["fsh"] else "")
    if c["nc"]: s += f" C{c['nc']}@{c['cwin']}"
    if c["gala"]: s += " GALA"
    if c["both"]: s += " BOTH"
    return s


def f(x, w=5, d=1):
    return " " * (w - 1) + "-" if x is None else f"{x:{w}.{d}f}"


def line(rec):
    c = rec["cfg"]; m = rec["m"]; A = m["ALL"]; P = m["PICK"]; J = m["JUDGE"]; ch = m["chain"]
    return (f"{desc(c):46s}| {f(A['pass_'])} {f(A['stuck'])} {f(A['run'])} | {f(A['p30'])} {f(A['p45'])} {f(A['p60'])} {f(A['med'], 5, 0)} {f(A['p75'], 5, 0)} | "
            f"{f(P['pass_'])} {f(P['p60'])} | {f(J['pass_'])} {f(J['p60'])} | {f(ch.get('ch_days'), 5, 0)} {f(ch.get('ch_att'), 5, 2)} {f(ch.get('ch_cens'))} {f(ch.get('rmst250'), 6, 1)} {f(ch.get('chp250'))} | "
            f"{m['static']['ALL']['profit']:7.0f} {m['static']['ALL']['tpw']:4.1f}")


HEAD = (f"{'config':46s}| {'pass':>5} {'stuck':>5} {'run':>5} | {'p30':>5} {'p45':>5} {'p60':>5} {'med':>5} {'p75':>5} | {'Ppass':>5} {'Pp60':>5} | {'Jpass':>5} {'Jp60':>5} | "
        f"{'chD':>5} {'att':>5} {'cens':>5} {'rmst250':>6} {'chp250':>5} | {'profit':>7} {'tpw':>4}")


def load(fn=None):
    fn = fn or os.environ.get("PF50_STORE", "/tmp/claude-0/-home-user-opogabuuga/a242e4b9-b41b-5028-bba9-c21e825f6a98/scratchpad/pf50/store.pkl")
    return pickle.load(open(fn, "rb"))


if __name__ == "__main__":
    d = load()
    recs = list(d.values())
    key = sys.argv[1] if len(sys.argv) > 1 else "p60"
    minpass = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
    top = int(sys.argv[3]) if len(sys.argv) > 3 else 40
    recs = [r for r in recs if r["m"]["ALL"]["pass_"] >= minpass]
    recs.sort(key=lambda r: -r["m"]["ALL"][key])
    print(HEAD)
    for r in recs[:top]: print(line(r))
