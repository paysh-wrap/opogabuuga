# Calculator fix notes (2026-11-24) - UNVERIFIED research projection
Case: Lucid PRO 150K, 5 accounts, 9 micros, fixed, payout every 2 weeks.
## Root cause (no arithmetic bug; the figures were mixed-basis and mislabelled)
1. Headline averages were taken over ALL simulated starts, including 56% that never get a payout (median 0, mean pulled down), while "per payout" was the mean over payouts actually paid. Different bases shown side by side looked inconsistent.
2. "Per 2-week payout" = mean size of one payout event ($2,977 net per account, below the net cap 0.9 x 3,500 = 3,150), x5 accounts = $14,885. Label implied "income per 2-week period". Not per account vs all accounts anywhere.
3. Per week = year total / 50 weeks (250 sessions), not x52.
4. Most possible 76,500 = 5 accounts x 0.9 x (3,000 + 4 x 3,500) = 5 x 15,300 (max 5 payouts, yaml `payout.max_payouts`); formula was not shown.
5. Median 0 with 43.2% paid is correct (<50% paid), but unexplained. Payout consistency in the sim was 35% (legacy); current is 40%: fixed to 40%.
## Fix
Headline = PROFIT SCENARIO (starts with >=1 payout, all N accounts assumed paid, net of 90% split; per account / all N net / all N gross), tooltips per row, formula line, and a note under the figures with X% paid, Y% busts and the unconditional figures. Data file keeps both bases.
## Before / after (per account is x5 for all 5)
Before: week $353, payout $14,885, year avg $17,630, median $0, middle half $0-45,000.
After (40% consistency regen): see UI; per account paid-scenario year avg $9,015, median $9,000, middle half $5,850-12,150, week $180 (all 5: $902 / 45,077 / 45,000 / 29,250-60,750), per payout $2,965 per account, most possible $76,500 (formula shown); incl. unpaid: avg $19,730 year, median $0; 43.8% paid, 64.4% bust.
