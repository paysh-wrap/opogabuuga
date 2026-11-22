
## 150K  (39315 configs)  BASE pass 77.1 med 159.0 profit 57879 judge 59.3 pick 65.1
BUILT N5@100+C4 both->2 at cushion<=1500 | 74.3 | 86.0 | 20.4 | 130 | 64.5 | 66.7 | 98728 | 17.0 | s$100 N5[1500>2] C4[1500>2] | needs-code(CANDACE size/brake)
feasible (pass>=70, profit>=BASE, judge, pick): 4885; best pass overall 91.1

Top-5 by median days
| pass | med d | w60 % | d to pass w/ resets | judge | pick | profit | stuck | config |
|---|---|---|---|---|---|---|---|---|
| 70.4 | 78.0 | 23.2 | 150 | 61.1 | 68.7 | 94850 | 18.8 | s$100 N5[2250>3,1500>2] C2[1500>1] grow[500.0, 6] dl0.7 lock80 | needs-code(CANDACE size/brake) |
| 70.9 | 79.0 | 22.9 | 148 | 62.1 | 68.7 | 94850 | 18.2 | s$100 N5[2250>3,1500>2] C2[1500>1] grow[500.0, 6] dl0.5 lock80 | needs-code(CANDACE size/brake) |
| 70.0 | 79.0 | 22.3 | 149 | 62.6 | 67.3 | 94089 | 19.3 | s$100 N5[2250>3,1500>2] C2[1500>1] grow[500.0, 6] dl0.5 lock80 cw1030 | needs-code(CANDACE size/brake) |
| 70.7 | 81.0 | 22.4 | 127 | 62.1 | 69.3 | 100575 | 20.6 | s$100 N5[1500>4,900>2] C5[2250>3,1500>1] | needs-code(CANDACE size/brake) |
| 70.9 | 81.0 | 22.3 | 126 | 62.6 | 69.3 | 100575 | 20.4 | s$100 N5[1500>4,900>2] C5[2250>3,1500>1] dl0.7 | needs-code(CANDACE size/brake) |

Pareto (pass vs median), feasible
| pass | med d | w60 % | d to pass w/ resets | judge | pick | profit | stuck | config |
|---|---|---|---|---|---|---|---|---|
| 90.2 | 144.0 | 3.4 | 181 | 82.6 | 63.3 | 63930 | 0.0 | s$100 N3[2250>2,1500>1] C5[2250>2,900>1] lock80 | needs-code(CANDACE size/brake) |
| 89.9 | 140.0 | 3.3 | 180 | 82.0 | 63.3 | 63930 | 0.0 | s$100 N3[2250>2,1500>1] C5[2250>2,900>1] dl0.5 lock80 | needs-code(CANDACE size/brake) |
| 89.1 | 121.0 | 10.2 | 166 | 80.7 | 69.7 | 80460 | 0.0 | s$100 N4[1800>2,1500>1] C4[2250>2,1500>1] | needs-code(CANDACE size/brake) |
| 88.4 | 119.0 | 10.7 | 166 | 79.4 | 69.3 | 82308 | 0.0 | s$100 N4[1800>2,1500>1] C5[2250>2,1500>1] | needs-code(CANDACE size/brake) |
| 87.4 | 102.0 | 19.6 | 157 | 77.6 | 70.9 | 97023 | 4.5 | s$100 N5[2250>2,1500>1] C4[1500>1] dl0.7 lock80 cw1030 | needs-code(CANDACE size/brake) |
| 86.8 | 101.0 | 19.5 | 159 | 76.6 | 70.9 | 97023 | 4.5 | s$100 N5[2250>2,1800>1] C4[1500>1] dl0.7 lock80 cw1030 | needs-code(CANDACE size/brake) |
| 83.8 | 99.0 | 20.9 | 157 | 71.2 | 70.4 | 98490 | 4.6 | s$100 N5[2250>2,1800>1] C5[1500>1] dl0.5 lock80 cw1030 | needs-code(CANDACE size/brake) |
| 83.3 | 98.0 | 19.2 | 154 | 71.1 | 72.0 | 98672 | 6.0 | s$100 N5[2250>1] C5[1800>4,1500>1] dl0.7 cw1030 | needs-code(CANDACE size/brake) |
| 83.0 | 96.0 | 24.8 | 152 | 69.8 | 72.0 | 98490 | 5.0 | s$100 N5[2250>1] C5[1800>4,1500>1] grow[500.0, 6] dl0.5 lock80 cw1030 | needs-code(CANDACE size/brake) |
| 81.2 | 95.0 | 24.6 | 148 | 66.7 | 72.0 | 98490 | 6.6 | s$100 N5[2250>3,1800>1] C5[1500>2,900>1] grow[500.0, 6] dl0.5 lock80 cw1030 | needs-code(CANDACE size/brake) |
| 81.1 | 94.0 | 24.6 | 151 | 66.4 | 72.0 | 98490 | 6.8 | s$100 N5[2250>3,1800>1] C5[1500>2,900>1] grow[500.0, 6] dl0.7 lock80 cw1030 | needs-code(CANDACE size/brake) |
| 80.4 | 93.0 | 26.1 | 144 | 65.2 | 72.0 | 100392 | 4.2 | s$100 N5[2250>3,1800>1] C5[1500>2,900>1] grow[500.0, 6] dl0.7 lock80 | needs-code(CANDACE size/brake) |
| 79.3 | 92.0 | 21.2 | 158 | 63.7 | 72.8 | 96638 | 5.8 | s$100 N5[2250>2,1500>1] C5[1800>3,1500>1] dl0.5 lock120 cw1030 | needs-code(CANDACE size/brake) |
| 79.1 | 89.5 | 26.4 | 145 | 62.8 | 72.9 | 100575 | 2.4 | s$100 N5[2250>3,1800>1] C5[1500>2,900>1] grow[500.0, 6] dl0.5 | needs-code(CANDACE size/brake) |
| 78.1 | 87.5 | 25.0 | 137 | 61.1 | 73.1 | 98728 | 2.6 | s$100 N5[2250>2,1500>1] C4[1800>2,900>1] grow[500.0, 6] dl0.5 | needs-code(CANDACE size/brake) |
| 78.0 | 87.0 | 24.8 | 143 | 61.0 | 73.1 | 98728 | 3.0 | s$100 N5[2250>2,1500>1] C4[1500>2,900>1] grow[500.0, 6] dl0.7 | needs-code(CANDACE size/brake) |
| 76.9 | 85.0 | 25.6 | 143 | 59.0 | 72.9 | 100575 | 1.8 | s$100 N5[2250>2,1800>1] C5[2250>4,1500>1] grow[500.0, 6] dl0.5 | needs-code(CANDACE size/brake) |
| 76.4 | 82.0 | 25.9 | 145 | 58.0 | 72.8 | 100575 | 2.6 | s$100 N5[2250>2,1500>1] C5[2700>4,1500>1] grow[500.0, 6] dl0.7 | needs-code(CANDACE size/brake) |
| 70.9 | 79.0 | 22.9 | 148 | 62.1 | 68.7 | 94850 | 18.2 | s$100 N5[2250>3,1500>2] C2[1500>1] grow[500.0, 6] dl0.5 lock80 | needs-code(CANDACE size/brake) |
| 70.4 | 78.0 | 23.2 | 150 | 61.1 | 68.7 | 94850 | 18.8 | s$100 N5[2250>3,1500>2] C2[1500>1] grow[500.0, 6] dl0.7 lock80 | needs-code(CANDACE size/brake) |

Best pass any (constraints ok) top-3 by pass
| pass | med d | w60 % | d to pass w/ resets | judge | pick | profit | stuck | config |
|---|---|---|---|---|---|---|---|---|
| 90.2 | 144.0 | 3.4 | 181 | 82.6 | 63.3 | 63930 | 0.0 | s$100 N3[2250>2,1500>1] C5[2250>2,900>1] lock80 | needs-code(CANDACE size/brake) |
| 90.2 | 144.0 | 3.4 | 190 | 82.6 | 63.3 | 63930 | 0.0 | s$100 N3[2250>1] C5[1500>1] lock80 | needs-code(CANDACE size/brake) |
| 90.2 | 145.0 | 3.4 | 173 | 82.6 | 63.3 | 63930 | 0.0 | s$100 N3[2250>2] C5[2250>2] lock80 | needs-code(CANDACE size/brake) |

## 100K  (14903 configs)  BASE pass 77.7 med 152.0 profit 38586 judge 60.4 pick 65.1
BUILT N2@250(1<750)+C4(1<1500) | 80.4 | 121.0 | 6.0 | 159 | 65.7 | 64.0 | 46697 | 9.1 | s$250 N2[750>1] C4[1500>1] | needs-code(CANDACE size/brake)
BUILT N2@250+C3 (old built) | 80.0 | 129.0 | 5.9 | 164 | 64.7 | 64.0 | 44850 | 8.9 | s$250 N2[750>1] C3[1500>1] | needs-code(CANDACE size/brake)
feasible (pass>=70, profit>=BASE, judge, pick): 2399; best pass overall 90.4

Top-5 by median days
| pass | med d | w60 % | d to pass w/ resets | judge | pick | profit | stuck | config |
|---|---|---|---|---|---|---|---|---|
| 70.4 | 87.0 | 18.6 | 138 | 58.0 | 67.8 | 62192 | 21.1 | s$100 N3[1000>1] C4[1500>3,1000>1] | needs-code(CANDACE size/brake) |
| 70.6 | 87.0 | 18.5 | 137 | 58.3 | 67.8 | 62192 | 20.7 | s$100 N3[1000>1] C4[1500>3,1000>1] dl0.7 | needs-code(CANDACE size/brake) |
| 70.4 | 87.0 | 18.4 | 137 | 58.0 | 67.8 | 62192 | 20.7 | s$100 N3[1000>1] C4[1500>3,1000>1] dl0.5 | needs-code(CANDACE size/brake) |
| 71.4 | 87.0 | 14.9 | 131 | 65.8 | 68.9 | 60345 | 20.0 | s$100 N3[1000>2] C3[600>2] dl0.5 | needs-code(CANDACE size/brake) |
| 71.4 | 87.0 | 14.9 | 131 | 65.8 | 68.9 | 60345 | 20.0 | s$100 N3[1000>2] C3[600>2] dl0.7 | needs-code(CANDACE size/brake) |

Pareto (pass vs median), feasible
| pass | med d | w60 % | d to pass w/ resets | judge | pick | profit | stuck | config |
|---|---|---|---|---|---|---|---|---|
| 90.4 | 138.0 | 4.1 | 183 | 83.0 | 64.2 | 43925 | 0.0 | s$100 N2[1500>1] C4[2000>1] | needs-code(CANDACE size/brake) |
| 90.1 | 137.0 | 5.4 | 173 | 82.4 | 63.3 | 45700 | 0.0 | s$100 N2[1500>1] C5[1500>3] lock80 | needs-code(CANDACE size/brake) |
| 89.9 | 135.0 | 3.8 | 182 | 82.0 | 64.2 | 43925 | 0.0 | s$100 N2[1500>1] C4[2000>1] dl0.5 | needs-code(CANDACE size/brake) |
| 85.8 | 130.5 | 4.1 | 183 | 74.8 | 63.3 | 43852 | 4.6 | s$100 N2[1500>1] C4[2000>1] lock80 | needs-code(CANDACE size/brake) |
| 85.5 | 127.0 | 4.0 | 182 | 74.3 | 63.3 | 43852 | 4.6 | s$100 N2[1500>1] C4[2000>1] dl0.5 lock80 | needs-code(CANDACE size/brake) |
| 83.7 | 112.5 | 23.1 | 156 | 71.1 | 69.7 | 43852 | 4.5 | s$100 N2[1500>1] C4[1800>2,1000>1] grow[1000.0, 12] dl0.5 lock80 | needs-code(CANDACE size/brake) |
| 82.2 | 106.0 | 20.5 | 152 | 68.4 | 71.1 | 43925 | 1.4 | s$100 N2[1500>1] C4[1500>2,1000>1] grow[1000.0, 12] dl0.5 | needs-code(CANDACE size/brake) |
| 81.1 | 105.0 | 22.8 | 151 | 66.4 | 69.7 | 43852 | 4.9 | s$100 N2[1500>1] C4[1500>2,1000>1] grow[1000.0, 12] dl0.5 lock80 | needs-code(CANDACE size/brake) |
| 79.4 | 100.0 | 22.2 | 142 | 63.4 | 72.0 | 43111 | 5.0 | s$100 N2[1500>1] C4[1800>2,1000>1] grow[1000.0, 12] dl0.5 lock120 | needs-code(CANDACE size/brake) |
| 78.4 | 94.5 | 14.9 | 145 | 64.0 | 69.1 | 60345 | 12.1 | s$100 N3[1500>2,1000>1] C3[1500>2,1000>1] dl0.5 | needs-code(CANDACE size/brake) |
| 77.4 | 94.0 | 18.1 | 136 | 59.9 | 70.9 | 62192 | 11.0 | s$100 N3[1500>1] C4[1500>2,600>1] dl0.5 | needs-code(CANDACE size/brake) |
| 73.6 | 93.0 | 13.6 | 137 | 62.0 | 71.3 | 58498 | 16.7 | s$100 N3[1500>2] C2[1500>1] dl0.7 | needs-code(CANDACE size/brake) |
| 72.8 | 91.0 | 18.4 | 137 | 67.0 | 67.5 | 60236 | 19.0 | s$100 N3[1000>2] C3[600>2] dl0.5 lock80 | needs-code(CANDACE size/brake) |
| 71.5 | 90.0 | 18.1 | 143 | 62.1 | 68.0 | 60236 | 18.6 | s$100 N3[1500>2] C3[1500>1] dl0.7 lock80 | needs-code(CANDACE size/brake) |
| 71.4 | 87.0 | 14.9 | 131 | 65.8 | 68.9 | 60345 | 20.0 | s$100 N3[1000>2] C3[600>2] dl0.5 | needs-code(CANDACE size/brake) |

Best pass any (constraints ok) top-3 by pass
| pass | med d | w60 % | d to pass w/ resets | judge | pick | profit | stuck | config |
|---|---|---|---|---|---|---|---|---|
| 90.4 | 138.0 | 4.1 | 183 | 83.0 | 64.2 | 43925 | 0.0 | s$100 N2[1500>1] C4[2000>1] | needs-code(CANDACE size/brake) |
| 90.1 | 137.0 | 5.4 | 173 | 82.4 | 63.3 | 45700 | 0.0 | s$100 N2[1500>1] C5[1500>3] lock80 | needs-code(CANDACE size/brake) |
| 90.1 | 145.0 | 5.4 | 181 | 82.4 | 63.3 | 45700 | 0.0 | s$100 N2[1500>1] C5[1500>1] lock80 | needs-code(CANDACE size/brake) |

## 50K  (4537 configs)  BASE pass 68.8 med 92.0 profit 38586 judge 55.3 pick 73.1
feasible (pass>=70, profit>=BASE, judge, pick): 9; best pass overall 90.3

Top-5 by median days
| pass | med d | w60 % | d to pass w/ resets | judge | pick | profit | stuck | config |
|---|---|---|---|---|---|---|---|---|
| 72.0 | 90.0 | 21.5 | 131 | 62.3 | 72.0 | 39267 | 17.2 | s$250 N2[1000>1] C0[-] dl0.7 lock80 | config-only |
| 72.0 | 90.0 | 21.5 | 131 | 62.3 | 72.0 | 39267 | 17.2 | s$250 N2[1000>1] C0[-] dl0.5 lock80 | config-only |
| 71.7 | 90.0 | 21.5 | 131 | 61.8 | 72.0 | 39267 | 17.4 | s$250 N2[1000>1] C0[-] lock80 | config-only |
| 70.4 | 91.5 | 18.8 | 132 | 58.2 | 73.9 | 38586 | 20.9 | s$250 N2[1000>1] C0[-] tap[0.25, 1] | config-only |
| 70.4 | 91.5 | 18.8 | 132 | 58.2 | 73.9 | 38586 | 20.9 | s$250 N2[1000>1] C0[-] tap[0.25, 1] dl0.7 | config-only |

Pareto (pass vs median), feasible
| pass | med d | w60 % | d to pass w/ resets | judge | pick | profit | stuck | config |
|---|---|---|---|---|---|---|---|---|
| 73.2 | 94.0 | 18.7 | 134 | 64.5 | 72.0 | 39267 | 17.2 | s$250 N2[1000>1] C0[-] tap[0.25, 1] lock80 | config-only |
| 72.0 | 90.0 | 21.5 | 131 | 62.3 | 72.0 | 39267 | 17.2 | s$250 N2[1000>1] C0[-] dl0.7 lock80 | config-only |

Best pass any (constraints ok) top-3 by pass
| pass | med d | w60 % | d to pass w/ resets | judge | pick | profit | stuck | config |
|---|---|---|---|---|---|---|---|---|
| 73.2 | 94.0 | 18.7 | 134 | 64.5 | 72.0 | 39267 | 17.2 | s$250 N2[1000>1] C0[-] tap[0.25, 1] lock80 | config-only |
| 73.2 | 95.0 | 18.7 | 135 | 64.5 | 72.0 | 39267 | 17.2 | s$250 N2[1000>1] C0[-] tap[0.25, 1] dl0.7 lock80 | config-only |
| 73.0 | 94.5 | 18.7 | 134 | 64.1 | 72.0 | 39267 | 17.4 | s$250 N2[1000>1] C0[-] tap[0.25, 1] dl0.5 lock80 | config-only |

## 25K  (1630 configs)  BASE pass 58.6 med 74.0 profit 19293 judge 38.6 pick 58.9
feasible (pass>=70, profit>=BASE, judge, pick): 0; best pass overall 63.5

Best pass (profit>=BASE, judge/pick ok)
| pass | med d | w60 % | d to pass w/ resets | judge | pick | profit | stuck | config |
|---|---|---|---|---|---|---|---|---|
| 62.5 | 56.0 | 34.4 | 95 | 56.0 | 62.5 | 19328 | 29.8 | s$75 N1[-] C2[600>1] dl0.5 | needs-code(CANDACE size/brake) |
| 62.5 | 56.0 | 34.4 | 95 | 56.0 | 62.5 | 19328 | 29.8 | s$75 N1[-] C2[600>1] tap[0.25, 1] dl0.5 | needs-code(CANDACE size/brake) |
| 62.5 | 57.0 | 33.9 | 95 | 56.0 | 62.5 | 19328 | 29.8 | s$75 N1[-] C2[600>1] dl0.7 | needs-code(CANDACE size/brake) |

Best pass any (constraints ok) top-3 by pass
| pass | med d | w60 % | d to pass w/ resets | judge | pick | profit | stuck | config |
|---|---|---|---|---|---|---|---|---|
| 62.5 | 56.0 | 34.4 | 95 | 56.0 | 62.5 | 19328 | 29.8 | s$75 N1[-] C2[600>1] dl0.5 | needs-code(CANDACE size/brake) |
| 62.5 | 56.0 | 34.4 | 95 | 56.0 | 62.5 | 19328 | 29.8 | s$75 N1[-] C2[600>1] tap[0.25, 1] dl0.5 | needs-code(CANDACE size/brake) |
| 62.5 | 57.0 | 33.9 | 95 | 56.0 | 62.5 | 19328 | 29.8 | s$75 N1[-] C2[600>1] dl0.7 | needs-code(CANDACE size/brake) |
