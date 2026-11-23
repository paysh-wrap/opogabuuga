"""Pull 30d Yahoo data (yfinance == OpenBB yfinance provider). Run in the scratch venv."""
import sys, time, yfinance as yf
OUT = sys.argv[1]
for name, cands in {"MGC": ["MGC=F", "GC=F"], "MNQ": ["MNQ=F", "NQ=F"], "MES": ["MES=F", "ES=F"]}.items():
    for t in cands:
        for iv in ("2m", "5m"):
            for k in range(5):
                try:
                    df = yf.Ticker(t).history(period="30d", interval=iv, prepost=True, auto_adjust=False)
                    break
                except Exception as e:
                    print(t, iv, "err", repr(e)[:100]); time.sleep(2 ** k); df = None
            if df is not None and len(df) > 500:
                df.to_csv(f"{OUT}/{name}_{t.replace('=','')}_{iv}.csv")
                print(name, t, iv, len(df), df.index[0], df.index[-1]); break
        else: continue
        break
