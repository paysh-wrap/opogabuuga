"""Runs INSIDE the isolated TradingAgents venv (never imported by the trading process).

Protocol: one JSON object on stdin, one JSON object on stdout.
  {"cmd": "version"}                       -> {"ok": true, "version": "0.7.1"}
  {"cmd": "catalog"}                       -> {"ok": true, "catalog": {...}}
  {"cmd": "run", "ticker": "QQQ", "date": "YYYY-MM-DD"} -> {"ok": true, "rating": "Buy", "decision": "..."}
API keys and model choices arrive via environment variables only.
"""

import json
import sys


def main() -> None:
    req = json.loads(sys.stdin.read() or "{}")
    cmd = req.get("cmd")
    try:
        import tradingagents

        if cmd == "version":
            out = {"ok": True, "version": tradingagents.__version__}
        elif cmd == "catalog":
            from tradingagents.llm_clients import model_catalog

            cat = getattr(model_catalog, "MODEL_OPTIONS", None) or getattr(model_catalog, "MODEL_CATALOG", {})
            out = {
                "ok": True,
                "catalog": {
                    p: {tier: [m[1] for m in opts if m[1] != "custom"] for tier, opts in tiers.items()}
                    for p, tiers in cat.items()
                    if isinstance(tiers, dict)
                },
            }
        elif cmd == "run":
            from tradingagents.default_config import build_default_config
            from tradingagents.graph.trading_graph import TradingAgentsGraph

            ta = TradingAgentsGraph(debug=False, config=build_default_config())
            final_state, rating = ta.propagate(req["ticker"], req["date"])
            out = {
                "ok": True,
                "rating": str(rating),
                "decision": str(final_state.get("final_trade_decision", ""))[:20000],
                "version": tradingagents.__version__,
            }
        else:
            out = {"ok": False, "error": f"unknown cmd {cmd!r}"}
    except Exception as e:  # report every failure; caller maps it to NO_TRADE + alert
        out = {"ok": False, "error": f"{type(e).__name__}: {e}"[:2000]}
    sys.stdout.write(json.dumps(out))


if __name__ == "__main__":
    main()
