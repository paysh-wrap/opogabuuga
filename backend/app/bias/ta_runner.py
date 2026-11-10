"""Runs INSIDE the isolated TradingAgents venv (never imported by the trading process).

Protocol: one JSON object on stdin, one JSON object on stdout.
  {"cmd": "version"}                       -> {"ok": true, "version": "0.7.1"}
  {"cmd": "catalog"}                       -> {"ok": true, "catalog": {...}}
  {"cmd": "run", "ticker": "QQQ", "date": "YYYY-MM-DD"} -> {"ok": true, "rating": "Buy", "decision": "..."}
  {"cmd": "research", "ticker": "GLD", "date": "YYYY-MM-DD", "market": "MGC", "context": {...}}
      -> {"ok": true, "setup": {side, confidence, entry_low, entry_high, invalidation, target, valid_until, reasons},
          "rating": "...", "report": "...", "version": "..."}      (D84 MGC research: gold drivers → structured setup)
API keys and model choices arrive via environment variables only.
"""

import json
import re
import sys
from typing import Any

_SETUP = re.compile(r"TA_SETUP\s*(\{.*\})", re.S)
REPORT_KEYS = ("market_report", "sentiment_report", "news_report", "fundamentals_report", "investment_plan")


def research_prompt(req: dict[str, Any], decision: str, reports: dict[str, Any]) -> str:
    """D84: gold-focused structured-setup request (the app validates every number; the model only proposes)."""
    ctx = json.dumps(req.get("context") or {}, default=str)[:3000]
    rep = json.dumps(reports, default=str)[:6000]
    return (
        f"You are a gold futures research desk. Market: {req.get('market', 'MGC')} (Micro Gold, tick 0.10) via proxy "
        f"{req.get('ticker')}; session date {req.get('date')} (US/Eastern). Weigh the gold drivers: US dollar / DXY, "
        "real yields, Fed and CPI (macro calendar below), risk sentiment, and trend / key levels. "
        f"Context (prices, calendar): {ctx}. TradingAgents' own analysis: decision={decision[:2500]!r} reports={rep}. "
        "Propose ONE intraday setup for the London open to 11:30 ET, or none. Reward-to-risk is measured from the "
        "entry zone to the invalidation price: set the target at about 2R (1:2 preferred, never below 1.5R). "
        "Finish with exactly one line, nothing after it:\n"
        'TA_SETUP {"side": "LONG" or "SHORT" or "NONE", "confidence": integer 0-100, "entry_low": number, '
        '"entry_high": number, "invalidation": number, "target": number, "valid_until": "HH:MM" (ET), '
        '"reasons": ["max 5 short strings"]}'
    )


def parse_setup_line(text: str) -> dict[str, Any] | None:
    """Last TA_SETUP line → dict; anything malformed → None (the app then records SETUP_MALFORMED)."""
    found = _SETUP.findall(text or "")
    if not found:
        return None
    try:
        d = json.loads(found[-1])
    except ValueError:
        return None
    return d if isinstance(d, dict) else None


def finish_research(
    req: dict[str, Any], final_state: dict[str, Any], rating: object, llm: object, version: str
) -> dict[str, Any]:
    """Second step of `research`: turn TradingAgents' analysis + the gold context into the structured setup using the
    SAME quick-think LLM TradingAgents was configured with (same key, no new connection)."""
    decision = str(final_state.get("final_trade_decision", ""))
    reports = {k: str(final_state.get(k, ""))[:1500] for k in REPORT_KEYS if final_state.get(k)}
    invoke = getattr(llm, "invoke", None)
    if invoke is None:
        return {"ok": False, "error": "structured setup unavailable: TradingAgents exposes no LLM handle"}
    resp = invoke(research_prompt(req, decision, reports))
    text = str(getattr(resp, "content", resp))
    return {
        "ok": True,
        "setup": parse_setup_line(text),
        "rating": str(rating),
        "report": (decision + "\n\n" + text)[:20000],
        "version": version,
    }


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
        elif cmd == "research":
            from tradingagents.default_config import build_default_config
            from tradingagents.graph.trading_graph import TradingAgentsGraph

            ta = TradingAgentsGraph(debug=False, config=build_default_config())
            final_state, rating = ta.propagate(req["ticker"], req["date"])
            out = finish_research(
                req, final_state, rating, getattr(ta, "quick_thinking_llm", None), tradingagents.__version__
            )
        else:
            out = {"ok": False, "error": f"unknown cmd {cmd!r}"}
    except Exception as e:  # report every failure; caller maps it to NO_TRADE + alert
        out = {"ok": False, "error": f"{type(e).__name__}: {e}"[:2000]}
    sys.stdout.write(json.dumps(out))


if __name__ == "__main__":
    main()
