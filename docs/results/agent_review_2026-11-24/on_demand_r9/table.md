| group | mode | net/yr/acct all starts | net/yr paid-scenario | any payout % | bust % | median sessions to 1st | payouts/yr | lost trades/yr | pause days/yr |
|---|---|---|---|---|---|---|---|---|---|
| ALL 20 rows | weekly | 2397 | 3691 | 61.4 | 32.4 | 89 | 1.54 | 0.0 | 0.0 |
| ALL 20 rows | 2weeks | 2321 | 3611 | 60.9 | 32.2 | 92 | 1.43 | 0.0 | 0.0 |
| ALL 20 rows | daily_close | 2452 | 3752 | 61.9 | 32.5 | 86 | 1.64 | 0.0 | 0.0 |
| ALL 20 rows | on_demand | 840 | 1289 | 45.6 | 28.4 | 98 | 1.05 | 0.1 | 1.1 |
| ALL 20 rows | on_demand_nopause_counterfactual | 840 | 1288 | 45.6 | 28.4 | 98 | 1.05 | 0.0 | 0.0 |
| ALL 20 rows | on_demand_amount_not_session_limited_sensitivity | 2466 | 3767 | 61.9 | 32.8 | 85 | 1.65 | 0.4 | 1.7 |
| 25K | weekly | 1075 | 2321 | 45.5 | 69.7 | 63 | 1.22 | 0.0 | 0.0 |
| 25K | 2weeks | 1067 | 2342 | 44.9 | 69.3 | 64 | 1.14 | 0.0 | 0.0 |
| 25K | daily_close | 1072 | 2314 | 45.9 | 69.5 | 60 | 1.29 | 0.0 | 0.0 |
| 25K | on_demand | 0 | 0 | 0.0 | 59.5 | nan | 0.00 | 0.0 | 0.0 |
| 25K | on_demand_nopause_counterfactual | 0 | 0 | 0.0 | 59.5 | nan | 0.00 | 0.0 | 0.0 |
| 25K | on_demand_amount_not_session_limited_sensitivity | 1070 | 2294 | 45.9 | 70.3 | 60 | 1.29 | 0.4 | 1.3 |
| 50K | weekly | 2429 | 3991 | 63.1 | 38.9 | 76 | 1.72 | 0.0 | 0.0 |
| 50K | 2weeks | 2374 | 3914 | 62.7 | 38.6 | 80 | 1.61 | 0.0 | 0.0 |
| 50K | daily_close | 2458 | 4025 | 63.5 | 38.6 | 74 | 1.81 | 0.0 | 0.0 |
| 50K | on_demand | 884 | 1579 | 54.1 | 33.8 | 80 | 1.30 | 0.2 | 1.3 |
| 50K | on_demand_nopause_counterfactual | 884 | 1579 | 54.1 | 33.8 | 80 | 1.30 | 0.0 | 0.0 |
| 50K | on_demand_amount_not_session_limited_sensitivity | 2483 | 4050 | 63.7 | 38.6 | 74 | 1.83 | 0.5 | 1.8 |
| 100K | weekly | 3021 | 4223 | 71.2 | 18.1 | 96 | 1.71 | 0.0 | 0.0 |
| 100K | 2weeks | 2908 | 4096 | 70.5 | 17.9 | 102 | 1.57 | 0.0 | 0.0 |
| 100K | daily_close | 3133 | 4357 | 71.6 | 18.9 | 93 | 1.85 | 0.0 | 0.0 |
| 100K | on_demand | 1130 | 1633 | 66.2 | 17.4 | 99 | 1.47 | 0.0 | 1.5 |
| 100K | on_demand_nopause_counterfactual | 1130 | 1633 | 66.2 | 17.4 | 99 | 1.47 | 0.0 | 0.0 |
| 100K | on_demand_amount_not_session_limited_sensitivity | 3133 | 4358 | 71.6 | 18.9 | 91 | 1.86 | 0.4 | 1.9 |
| 150K | weekly | 3063 | 4227 | 66.0 | 3.1 | 120 | 1.51 | 0.0 | 0.0 |
| 150K | 2weeks | 2937 | 4091 | 65.2 | 3.0 | 124 | 1.41 | 0.0 | 0.0 |
| 150K | daily_close | 3143 | 4312 | 66.5 | 3.1 | 116 | 1.61 | 0.0 | 0.0 |
| 150K | on_demand | 1346 | 1943 | 62.2 | 2.9 | 116 | 1.43 | 0.3 | 1.4 |
| 150K | on_demand_nopause_counterfactual | 1344 | 1940 | 62.2 | 2.9 | 116 | 1.43 | 0.0 | 0.0 |
| 150K | on_demand_amount_not_session_limited_sensitivity | 3179 | 4364 | 66.5 | 3.1 | 115 | 1.62 | 0.3 | 1.6 |

Rows where on-demand pays at all (session profit >= $500 reachable): 15 of 20. On those rows, net/yr/acct (all starts): weekly 2838, 2weeks 2740, daily_close 2911, on_demand 1120, on_demand_nopause_counterfactual 1119, on_demand_amount_not_session_limited_sensitivity 2931
Rows (of 20) where each mode is best net/yr (excl. the counterfactual): {"weekly": 7, "2weeks": 2, "daily_close": 11, "on_demand": 0, "on_demand_nopause_counterfactual": 0, "on_demand_amount_not_session_limited_sensitivity": 0}
