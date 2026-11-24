"""Round 4 (agent B): entry quality / win rate / new combos. Research only. Frozen pre-registration in PREREG below
(thresholds set from PICK 2021-10..2023-12 quantiles only, then applied unchanged to JUDGE 2024-01..2026-10)."""
import pickle, json, numpy as np, pandas as pd
rng = np.random.default_rng(7)
D = pickle.load(open('/home/user/days.pkl', 'rb')); NQ = dict(D[0]); ES = D[1]
N = pd.read_csv('/tmp/claude-0/r3/streams/noise_s100_l100o10_m3_x.csv')          # built NOISE stream ($100 stop, lock 100/10, max3, Mondays skipped), $ per micro-unit
C = pd.read_csv('/home/user/paytience/docs/results/pass_faster_c125/streams_candace_base.csv')
C = C[(C.stop_pts * 2 + 2) <= 125]; C['pnl'] = C.p1 * 2.0 - 2.0; C['d'] = C.day; C['side'] = np.where(C.dir == 'LONG', 1, -1)
PICK = ('2021-10-01', '2023-12-31'); JUDGE = ('2024-01-01', '2026-10-31')
days = sorted(NQ); di = {d: i for i, d in enumerate(days)}
def rng_(d): b = NQ[d]; return b['high'].max() - b['low'].min()
R = {d: rng_(d) for d in days}
def feat(r):
    b = NQ[r.d]; k = int(r.ek); i = di[r.d]; px = b['open'][k]
    prev = [R[days[j]] for j in range(max(0, i - 20), i)]
    f = dict(vwapdist=r.side * (px - b['vwap'][k - 1]) / px * 1e4 if k > 0 else 0,
             prevreg=(R[days[i - 1]] / np.mean(prev)) if i > 1 else 1,
             fh=np.sign(b['close'][59] - b['open'][0]) * r.side if k >= 60 else 0,
             movesig=abs(px - b['open'][0]) / max(np.mean(prev), 1))
    e = ES.get(r.d)
    f['mesagree'] = np.sign(e['open'][k] - e['open'][0]) * r.side if e is not None else 0
    return pd.Series(f)
N = pd.concat([N, N.apply(feat, axis=1)], axis=1)
cd = C.groupby('d').side.first()
N['cdir'] = N.d.map(cd).fillna(0) * N.side
def stats(s):
    p = s.pnl.values; g = p[p > 0].sum(); l = -p[p < 0].sum()
    return dict(n=len(p), win=round((p > 0).mean() * 100, 1) if len(p) else 0, pf=round(g / l, 3) if l else 99, net=round(p.sum()))
def win(s, w): return s[(s.d >= w[0]) & (s.d <= w[1])]
def ctrl(base, keepmask, w):  # random-skip control: same keep fraction, p95 of PF and win
    b = win(base, w); m = keepmask.loc[b.index].values; f = m.mean(); out = []
    for _ in range(1000):
        r = b[rng.random(len(b)) < f]; s = stats(r); out.append((s['pf'], s['win']))
    o = np.array(out); return round(np.percentile(o[:, 0], 95), 3), round(np.percentile(o[:, 1], 95), 1)
pq = win(N, PICK)
Q = dict(vw80=pq.vwapdist.quantile(.8), reg80=pq.prevreg.quantile(.8), mv80=pq.movesig.quantile(.8))
PREREG = {  # NOISE filters (skip mask) -- frozen on pick
 'a1_skip_prevday_range_top20': N.prevreg > Q['reg80'],
 'a2_skip_vwapdist_top20': N.vwapdist > Q['vw80'],
 'a3_skip_firsthour_disagree': N.fh < 0,
 'a4_skip_move_from_open_top20': N.movesig > Q['mv80'],
 'a5_skip_MES_disagree': N.mesagree < 0,
 'b1_skip_if_CANDACE_opposite': N.cdir < 0,
 'b2_only_if_CANDACE_agrees_or_none': N.cdir < 0,  # same as b1 by construction; kept to count honestly -> replaced below
}
PREREG['b2_skip_if_no_CANDACE_trade'] = N.cdir == 0; del PREREG['b2_only_if_CANDACE_agrees_or_none']
res = {'quantiles': {k: round(float(v), 3) for k, v in Q.items()}, 'noise': {}, 'other': {}}
def yr(s): return {y: stats(g)['net'] for y, g in s.groupby(s.d.str[:4])}
res['noise']['BASE'] = {w: stats(win(N, W)) for w, W in (('pick', PICK), ('judge', JUDGE))}
for k, skip in PREREG.items():
    kept = N[~skip]; r = {}
    for w, W in (('pick', PICK), ('judge', JUDGE)):
        r[w] = stats(win(kept, W)); r[w]['ctrl_p95_pf_win'] = ctrl(N, ~skip, W)
    r['per_year'] = yr(kept); res['noise'][k] = r
# d1: shrink-only half size on NOISE when CANDACE opposite (sizes 1.0 / 0.5)
h = N.copy(); h.loc[h.cdir < 0, 'pnl'] *= 0.5
res['noise']['d1_half_size_if_CANDACE_opposite'] = {w: stats(win(h, W)) for w, W in (('pick', PICK), ('judge', JUDGE))}
# e: CANDACE refinements
ct = C.time.str.replace(':', '').astype(int)
for k, m in {'e1_CANDACE_skip_0958_1005': (ct >= 958) & (ct <= 1005), 'e2_CANDACE_grade_C_skip': C.grade == 'C'}.items():
    kept = C[~m]; res['other'][k] = {w: stats(win(kept, W)) for w, W in (('pick', PICK), ('judge', JUDGE))}
    res['other'][k]['pick_ctrl'] = ctrl(C, ~m, PICK); res['other'][k]['judge_ctrl'] = ctrl(C, ~m, JUDGE)
res['other']['CANDACE_BASE'] = {w: stats(win(C, W)) for w, W in (('pick', PICK), ('judge', JUDGE))}
# c: new legs, 1 micro-unit, $2 RT cost, $100 stop proxied by exit at worse of stop/time using 1-min high/low
def leg(fn):
    rows = []
    for d in days:
        if pd.Timestamp(d).dayofweek == 0: continue
        t = fn(d)
        if t: rows.append(t)
    return pd.DataFrame(rows, columns=['d', 'side', 'pnl'])
def run(d, k, side, end, stop=50.0):  # stop in points*2=$100 per micro
    b = NQ[d]; e = b['open'][k]
    for j in range(k, end):
        if side * (b['low'][j] if side > 0 else b['high'][j]) <= side * e - stop: return -stop * 2 - 2
    return side * (b['close'][end - 1] - e) * 2 - 2
def c1(d, rs=None):  # 14:00-15:00 range reversal: fade the 14-15 move if > 0.25 %, hold to 15:55
    b = NQ[d]; mv = b['close'][329] - b['open'][270]
    if abs(mv) / b['open'][270] < .0025: return None
    s = -np.sign(mv) if rs is None else rs.choice([-1, 1]); return (d, s, run(d, 330, s, 385))
def c2(d, rs=None):  # gap fade toward prior close, enter 09:35, exit 11:00
    i = di[d]
    if i == 0: return None
    pc = NQ[days[i - 1]]['close'][-1]; g = NQ[d]['open'][0] - pc
    if abs(g) / pc < .003: return None
    s = -np.sign(g) if rs is None else rs.choice([-1, 1]); return (d, s, run(d, 5, s, 90))
def c3(d, rs=None):  # ORB retest after CANDACE window: 10:30 break of 09:30-10:00 range in direction, hold to 12:00
    b = NQ[d]; hi, lo = b['high'][:30].max(), b['low'][:30].min(); px = b['close'][59]
    s = 1 if px > hi else (-1 if px < lo else 0)
    if not s: return None
    s = s if rs is None else rs.choice([-1, 1]); return (d, s, run(d, 60, s, 150))
def c4(d, rs=None):  # MES/MNQ divergence at 11:00: trade MNQ toward MES direction when they disagree
    e = ES.get(d)
    if e is None: return None
    b = NQ[d]; a = np.sign(b['close'][89] - b['open'][0]); m = np.sign(e['close'][89] - e['open'][0])
    if a == m or m == 0: return None
    s = m if rs is None else rs.choice([-1, 1]); return (d, s, run(d, 90, s, 240))
nd = N.groupby('d').pnl.sum(); cdd = C.groupby('d').pnl.sum()
for k, fn in {'c1_1400_reversal': c1, 'c2_gap_fade': c2, 'c3_orb_break_1030': c3, 'c4_MES_divergence': c4}.items():
    L = leg(fn); r = {w: stats(win(L, W)) for w, W in (('pick', PICK), ('judge', JUDGE))}
    ctl = []
    for s_ in range(200):
        rs = np.random.default_rng(s_); Lr = leg(lambda d: fn(d, rs)); ctl.append(stats(win(Lr, JUDGE))['net'])
    r['judge_random_dir_net_p95'] = round(np.percentile(ctl, 95)); r['per_year'] = yr(L)
    ld = L.groupby('d').pnl.sum()
    for nm, o in (('corr_noise', nd), ('corr_candace', cdd)):
        j = pd.concat([ld, o], axis=1).fillna(0); r[nm] = round(j.corr().iloc[0, 1], 3)
    res['other'][k] = r
json.dump(res, open('/home/user/paytience/docs/results/agent_review_2026-11-24/new_combos_r4/results_r4.json', 'w'), indent=1, default=str)
print(json.dumps(res, indent=1, default=str))
