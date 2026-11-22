
C40: BASE judge 59.3 pick 65.1 profit 57,879; U1 med 109; floors judge>=56.3 pick>=60.1; 155 configs, 41 robust, 38 robust with median < 109
C40 top 5 ROBUST by median days
| config (stop|NOISE|CAND|brake cushion/micros|taper|grow|daylock) | pass | <=60d | median | chain d | pick | judge | profit |
|---|---|---|---|---|---|---|---|
| s100|N5|c4|b2000/2|t0|g0|d1 | 71.2 | 19.9 | 83 | 134 | 67.6 | 58.2 | 98,728 |
| s100|N5|c4|b2000/2|t0|g0|d0 | 70.8 | 20.1 | 84 | 137 | 67.6 | 57.4 | 98,728 |
| s100|N5|c4|b1500/2|t0|g0|d1 | 74.7 | 20.2 | 85 | 129 | 66.7 | 65.2 | 98,728 |
| s100|N5|c4|b1500/2|t0|g0|d0 | 74.3 | 20.4 | 86 | 130 | 66.7 | 64.5 | 98,728 |
| s100|N4|c5|b1000/3|t0|g1|d1 | 70.0 | 18.1 | 87 | 132 | 70.0 | 62.8 | 82,308 |
C40 top 5 ROBUST by chain days (expected days to first pass with resets)
| config (stop|NOISE|CAND|brake cushion/micros|taper|grow|daylock) | pass | <=60d | median | chain d | pick | judge | profit |
|---|---|---|---|---|---|---|---|
| s100|N5|c4|b1500/2|t0|g0|d1 | 74.7 | 20.2 | 85 | 129 | 66.7 | 65.2 | 98,728 |
| s100|N5|c4|b1500/2|t0|g0|d0 | 74.3 | 20.4 | 86 | 130 | 66.7 | 64.5 | 98,728 |
| s100|N4|c5|b1000/3|t0|g1|d1 | 70.0 | 18.1 | 87 | 132 | 70.0 | 62.8 | 82,308 |
| s100|N5|c4|b2000/2|t0|g0|d1 | 71.2 | 19.9 | 83 | 134 | 67.6 | 58.2 | 98,728 |
| s100|N5|c4|b2000/2|t0|g0|d0 | 70.8 | 20.1 | 84 | 137 | 67.6 | 57.4 | 98,728 |
C40 top 3 by median ignoring robustness
  s125|N8|c5|b1500/2|t0|g0|d0: pass 41.1 med 46 pick 49.0 judge 34.9 profit 144,026
  s125|N8|c4|b1500/2|t0|g0|d0: pass 40.3 med 47 pick 49.2 judge 33.3 profit 142,178
  s150|N8|c5|b1500/2|t0|g0|d0: pass 40.1 med 47 pick 45.9 judge 35.0 profit 152,998

C50: BASE judge 59.7 pick 65.1 profit 57,879; U1 med 107; floors judge>=56.7 pick>=60.1; 155 configs, 57 robust, 49 robust with median < 107
C50 top 5 ROBUST by median days
| config (stop|NOISE|CAND|brake cushion/micros|taper|grow|daylock) | pass | <=60d | median | chain d | pick | judge | profit |
|---|---|---|---|---|---|---|---|
| s100|N5|c4|b1500/3|t0|g0|d1 | 71.6 | 20.5 | 79 | 135 | 68.2 | 69.4 | 98,728 |
| s100|N5|c4|b2000/2|t0|g0|d1 | 71.6 | 20.2 | 81 | 132 | 67.6 | 59.0 | 98,728 |
| s100|N5|c4|b1500/3|t0|g0|d0 | 71.5 | 20.8 | 81 | 136 | 68.2 | 69.1 | 98,728 |
| s100|N5|c2|b1500/3|t0|g0|d1 | 71.0 | 18.4 | 82 | 130 | 63.6 | 67.8 | 95,032 |
| s100|N5|c2|b1500/2|t0|g0|d1 | 72.0 | 18.4 | 83 | 128 | 68.7 | 57.7 | 95,032 |
C50 top 5 ROBUST by chain days (expected days to first pass with resets)
| config (stop|NOISE|CAND|brake cushion/micros|taper|grow|daylock) | pass | <=60d | median | chain d | pick | judge | profit |
|---|---|---|---|---|---|---|---|
| s100|N5|c4|b1500/2|t0|g0|d1 | 76.6 | 20.5 | 84 | 127 | 66.7 | 68.7 | 98,728 |
| s100|N5|c2|b1500/2|t0|g0|d1 | 72.0 | 18.4 | 83 | 128 | 68.7 | 57.7 | 95,032 |
| s100|N5|c4|b1500/2|t0|g0|d0 | 76.4 | 20.8 | 86 | 128 | 66.7 | 68.4 | 98,728 |
| s100|N5|c2|b1500/2|t0|g0|d0 | 71.8 | 18.4 | 84 | 129 | 68.7 | 57.3 | 95,032 |
| s100|N5|c2|b1500/3|t0|g0|d1 | 71.0 | 18.4 | 82 | 130 | 63.6 | 67.8 | 95,032 |
C50 top 3 by median ignoring robustness
  s150|N8|c5|b1500/2|t0|g0|d0: pass 43.8 med 43 pick 47.7 judge 40.3 profit 152,998
  s125|N8|c4|b1500/2|t0|g0|d0: pass 42.2 med 44 pick 49.9 judge 36.2 profit 142,178
  s125|N8|c5|b1500/2|t0|g0|d0: pass 43.2 med 44 pick 49.5 judge 38.3 profit 144,026