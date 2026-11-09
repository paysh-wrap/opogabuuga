# Agent H independent verification (script: verify.py, raw output: results.txt)
Own float simulator, 1305 weekday sessions, rules from the 4 lucid_pro yamls.
A. CONFIRMED (all 8 numbers: 150K $955/$881, bust 23.5/23.5; 100K $693/$643; 50K $608/$564, 48.6/44.2; 25K $340(339)/$317, 61.6/56.6).
3. CONFIRMED only if the eval is run WITHOUT the drawdown brake (what the original script does: eval_path called without brake=).
   With the brake applied in the eval (what the app would do): 50K size2 $1,666 (-5%), 100K size2 $2,194 (-6%), 150K size3 $3,094 (-3%); 25K $1,039 unchanged.
   Best eval size = funded size holds either way for 25K/50K/100K. For 150K with brake in eval, size 4 ($3,155) edges size 3 ($3,094), within 2%.
4. CONFIRMED: 150K same-day P0 25.2%, all-bust 23.5%, p25 $0; ~1 month 13.7% / 6.2% / $7,318; ~2 months 5.9% / 4.8% / $15,515 (claim $15,497, 0.1%). Mean 22.9k -> 24.3k -> 25.1k.
   Higher mean is an ARTIFACT: same-day starts restricted to the same start window (n=439, the 0/42/..168 window) average $27,073 vs staggered $25,090 (-7%).
   Staggering does not raise the mean; it cuts tail risk (P0 11.8% -> 5.9%, all-bust 11.8% -> 4.8% in the same window). Later-start windows simply exclude the bad early (2021-22) starts.
