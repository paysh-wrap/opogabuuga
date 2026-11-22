"""per plan: built row, then variants with median < built (sorted), with flags F=floor $=profit J=judge P=pick. python3 report.py [n]"""
import json, sys, os
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, H)
n = int(sys.argv[1]) if len(sys.argv) > 1 else 12
d = json.load(open(H + "/results.json"))
FLOOR = {25: 62, 50: 62, 100: 70, 150: 70}
BB = {150: dict(stop=100, N=5, nc=5, nb=((2250, 2), (1500, 1)), cb=((2700, 4), (1500, 1)), grow=(500., 6), dlock=0.7),
      100: dict(stop=100, N=3, nc=3, nb=((1000, 2),), cb=((600, 2),), dlock=0.5),
      50: dict(stop=75, N=2, nc=4, nb=((667, 1),), cb=((1000, 3),), dlock=0.5, lock=80),
      25: dict(stop=75, N=1, nc=2, cb=((333, 1),))}
nm = lambda k, p: f"{k}|" + json.dumps(p, sort_keys=True, default=list)
norm = lambda v: json.loads(json.dumps(v, default=list))
for k in (150, 100, 50, 25):
    b = norm(BB[k]); br = d[nm(k, dict(sorted(BB[k].items())))]
    print(f"\n{k}K built pass {br['ALL']['pass']:.1f} med {br['ALL']['med']} J {br['JUDGE']['pass']:.1f} P {br['PICK']['pass']:.1f} profit {br['profit']:.0f}")
    rows = [(key, r) for key, r in d.items() if key.startswith(f"{k}|") and (r['ALL']['med'] or 999) < br['ALL']['med']]
    for key, r in sorted(rows, key=lambda x: x[1]['ALL']['med'])[:n]:
        p = json.loads(key.split('|', 1)[1])
        diff = {x: v for x, v in p.items() if b.get(x) != v and not (x not in b and v in (None, False, []))}
        fl = "".join(["F" if r['ALL']['pass'] < FLOOR[k] else "", "$" if r['profit'] < br['profit'] else "",
                      "J" if r['JUDGE']['pass'] < br['JUDGE']['pass'] - 3 else "", "P" if r['PICK']['pass'] < br['PICK']['pass'] - 5 else ""]) or "OK"
        print(f"  {fl:4} pass {r['ALL']['pass']:.1f} med {r['ALL']['med']} J {r['JUDGE']['pass']:.1f} P {r['PICK']['pass']:.1f} profit {r['profit']:.0f} {diff}")
