"""Build Paytience_2week_income_breakdown.pdf from final_numbers.json (reportlab). usage: make_pdf.py IN.json OUT.pdf"""
import json
import sys

from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.shapes import Drawing, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

NAVY, BLUE, GOLD, GREY = colors.HexColor("#0A1020"), colors.HexColor("#1D4ED8"), colors.HexColor("#B8860B"), colors.HexColor("#E5E7EB")
data = json.load(open(sys.argv[1]))
rows = data["rows"]
ss = getSampleStyleSheet()
H1 = ParagraphStyle("h1", parent=ss["Title"], textColor=NAVY, fontSize=20, spaceAfter=6)
H2 = ParagraphStyle("h2", parent=ss["Heading2"], textColor=BLUE, spaceBefore=10, spaceAfter=4)
P = ParagraphStyle("p", parent=ss["BodyText"], fontSize=9.5, leading=13)
S = ParagraphStyle("s", parent=P, fontSize=8, leading=10.5, textColor=colors.HexColor("#374151"))
money = lambda v: f"${v:,.0f}"  # noqa: E731
pct = lambda v: f"{v * 100:.0f}%" if v <= 1 else f"{v:.0f}%"  # noqa: E731


def brake(r):
    return "—" if not r["brake"] else f"&lt;{r['brake'][0] * 100:.0f}% → {r['brake'][1]}"


HDR = ParagraphStyle("hdr", parent=ss["BodyText"], fontSize=7, leading=8.5, textColor=colors.white, fontName="Helvetica-Bold")


def table(rs, header, body, widths, hi=None):
    t = Table([[Paragraph(h, HDR) for h in header]] + body, colWidths=widths, repeatRows=1)
    st = [("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
          ("FONTSIZE", (0, 0), (-1, -1), 7.6), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
          ("ALIGN", (2, 1), (-1, -1), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
          ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GREY]), ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#9CA3AF"))]
    for i in hi or []:
        st += [("TEXTCOLOR", (0, i), (-1, i), GOLD), ("FONTNAME", (0, i), (-1, i), "Helvetica-Bold")]
    t.setStyle(TableStyle(st))
    return t


def main_table(family):
    rs = [r for r in rows if r["plan"].startswith(family)]
    hdr = ["Plan", "Profile", "Micros", "Brake", "Worst trade", "Eval pass/bust", "1 acct / 2 wk", "5 accts / 2 wk",
           "5 accts / yr (typical)", "5 accts / yr (avg)", "Funded bust yr1"]
    body, hi = [], []
    for i, r in enumerate(rs, start=1):
        e = r["eval250"] if r["micros"] >= 2 and "100" in r["plan"] or "150" in r["plan"] else r["eval120"]
        body.append([r["label"], r["profile"], str(r["micros"]), Paragraph(brake(r), S), money(r["worst_trade"]),
                     f"{e[0] * 100:.0f}% / {e[1] * 100:.0f}%", money(r["p1_2wk"]), money(r["p5_2wk"]),
                     money(r["p5_year_median"]), money(r["p5_year_mean"]), f"{r['bust_pct']:.0f}%"])
        if r["plan"].endswith("150k") and r["profile"] == "High risk" and family == "lucid_pro":
            hi.append(i)
    w = [0.62, 0.62, 0.42, 0.72, 0.6, 0.74, 0.62, 0.66, 0.82, 0.72, 0.62]
    return table(rs, hdr, body, [x * inch for x in w], hi)


def bars(r):
    d = Drawing(250, 120)
    c = VerticalBarChart()
    c.x, c.y, c.width, c.height = 30, 18, 205, 82
    c.data = [r["months5"]]
    c.categoryAxis.categoryNames = [f"m{i + 1}" for i in range(12)]
    c.categoryAxis.labels.fontSize = 6
    c.valueAxis.labels.fontSize = 6
    c.valueAxis.valueMin = 0
    c.bars[0].fillColor = BLUE
    d.add(c)
    d.add(String(30, 106, f"{r['label']} · {r['profile']}: avg 5-account income by month", fontSize=7, fillColor=NAVY))
    return d


doc = SimpleDocTemplate(sys.argv[2], pagesize=letter, leftMargin=0.45 * inch, rightMargin=0.45 * inch,
                        topMargin=0.5 * inch, bottomMargin=0.5 * inch, title="Paytience 2-week income breakdown")
el = [Paragraph("Paytience — 2-week income breakdown, Lucid 25K → 150K", H1),
      Paragraph(f"Finalized MAIN strategy (NOISE $250 stop + afternoon fade $250 stop, MNQ) · automatic size per account with "
                f"the drawdown brake (Regular / High-risk buttons) · Databento MNQ 1-minute replay {data['period']} "
                f"({data['sessions']} sessions) through each plan's own Lucid rules. Payout requested every 2 weeks, 90% split.", P),
      Spacer(1, 6),
      Paragraph("Summary", H2),
      Paragraph("• <b>Best overall:</b> Pro 150K. Regular (3 micros, brake to 2) ≈ <b>$881 every 2 weeks for 5 accounts</b>, typical "
                "first year $21,072, 24% of funded accounts bust in year 1. High risk (4 micros, brake to 2) ≈ <b>$952 / 2 wk</b>, "
                "typical year $23,706, bust 27%.", P),
      Paragraph("• <b>Per account</b>, divide the 5-account figures by 5 (accounts take the same trades, so they pay and bust together).", P),
      Paragraph("• <b>Pro beats Flex at every size</b> (Flex pays 50% of profit per payout and locks the loss limit on payout).", P),
      Paragraph("• <b>High risk only helps on 150K.</b> On 100K it pays the same as Regular with a lower typical year.", P),
      Paragraph("• <b>2024–2026 was harder than 2021–2023</b> (bust rates roughly double); accounts funded in 2025 mostly busted in "
                "the weak Jan/Jul 2026 months. Start with 1–2 accounts and scale after live results match.", P),
      Paragraph("Lucid Pro — all sizes", H2), main_table("lucid_pro"),
      Paragraph("Eval: 120 sessions for 25K/50K, 250 for 100K/150K (bigger targets). 'Typical' = median outcome; the 25% of worst "
                "start dates earn $0 on most plans. Eval fees not subtracted.", S),
      Paragraph("Lucid Flex — all sizes", H2), main_table("lucid_flex"),
      PageBreak(),
      Paragraph("Payouts and monthly income per plan (5 accounts)", H2)]
dist_hdr = ["Plan", "Profile", "0 payouts", "1", "2", "3", "4", "5", "≥1 payout", "Days to 1st", "Max/yr (5 accts)", "Middle half / yr"]
dist_body = [[r["label"], r["profile"]] + [f"{r['payout_dist'][str(k)] * 100:.0f}%" for k in range(6)] +
             [f"{r['payout_pct']:.0f}%", str(r["first_payout"] or "—"), money(r["max_year5"]), f"{money(r['p5_p25'])}–{money(r['p5_p75'])}"]
             for r in rows if r["plan"].startswith("lucid_pro")]
el.append(table(rows, dist_hdr, dist_body, [x * inch for x in (0.65, 0.65, 0.55, 0.4, 0.4, 0.4, 0.4, 0.4, 0.6, 0.6, 0.85, 1.25)]))
el.append(Spacer(1, 8))
chart_rows = [r for r in rows if r["plan"].startswith("lucid_pro") and not (r["profile"] == "High risk" and r["plan"] in ("lucid_pro_25k", "lucid_pro_50k"))]
grid = [[bars(chart_rows[i]), bars(chart_rows[i + 1]) if i + 1 < len(chart_rows) else ""] for i in range(0, len(chart_rows), 2)]
el.append(Table(grid, colWidths=[3.7 * inch, 3.7 * inch]))
el += [PageBreak(), Paragraph("The finalized strategy (what Paytience trades)", H2)]
for t in (
    "<b>NOISE</b> — intraday momentum on MNQ (Zarattini, Aziz & Barbon 2024): hourly checks 10:00–15:00 ET; enter when price closes "
    "outside the 14-day noise band; exit when the hourly close crosses back through the band/VWAP (trailing); flat 16:00; max 3/day; "
    "broker emergency stop $250 per micro.",
    "<b>Afternoon fade</b> — only on days NOISE has not traded: 13:00–15:29 ET, close beyond VWAP ± 2 standard deviations → fade "
    "back toward VWAP (target = VWAP), $250 stop per micro, flat 15:55, 1 per day. Fade trades PAPER accounts first.",
    "<b>Automatic size</b> (Strategy page buttons) — Regular: 25K 1 · 50K 2 · 100K 2 · 150K 3 micros. High risk: 100K 3 · 150K 4. "
    "<b>Drawdown brake</b> in both: when the cushion above the trailing loss limit falls below 30–50% of the limit, trade fewer "
    "micros (50K/150K: below 50%; 100K Regular: below 30%) until it recovers.",
    "<b>Every trade still passes all safety checks</b>: Lucid DLL / MLL room, kill switch, one position per account, no hedging, "
    "news blackouts, attestation, 16:40/16:44 flat. Default PAPER; LIVE needs the explicit live switches.",
    "5-year research: NOISE + fade 1,291 trades, 50% win, PF 1.33, +$25,345 at 1 micro, no losing full year. 21 win-rate filters and "
    "22 account rules were tested; only the drawdown brake passed both halves. Projection, not a promise.",
):
    el.append(Paragraph("• " + t, P))
el += [Paragraph("Next steps — start trading", H2)]
for t in (
    "1. <b>Pick the plan</b> on the Risk page that matches your Lucid accounts (the app applies one plan's firm rules to all accounts).",
    "2. <b>TradingView webhooks</b>: keep the 4 alerts pointing at your Cloudflare tunnel URL + webhook secret; MNQ1! 1-minute "
    "HEARTBEAT must be running (NOISE needs 10 stored RTH sessions before its first trade — the Strategy page shows the warm-up "
    "counter). Remember: TradingView Essential alerts expire every 2 months.",
    "3. <b>When heartbeats show on the Dashboard</b> (Markets panel / Signals page): add each Lucid account on the Automation page — "
    "Tradovate account ID, stage (EVAL/FUNDED), starting balance = the account size (this drives the automatic size).",
    "4. <b>Connect Tradovate</b> on Connections (token kept encrypted; password never stored). Run the pre-flight check; do the daily "
    "external-positions attestation; arm + select the accounts.",
    "5. <b>Run PAPER first</b> for at least 5 sessions (automation starts OFF → SEMI → FULL). Compare paper fills with the Strategy "
    "page numbers; only then use the live switches (PAYTIENCE_ALLOW_LIVE + typed confirmation + Live-Readiness Checklist).",
    "6. <b>Start with Regular sizing and 1–2 accounts</b>; add accounts and consider High risk on 150K once live results track the "
    "projection.",
    "7. <b>TradingAgents + Vibe-Trading</b>: they stay ADVISORY. Every daily call is scored in the calibration ledger; once ≥ 30 "
    "calls are proven (≥ 70% accuracy, Brier &lt; 0.25) the app lets a strongly-agreed call block the opposite NOISE side. That "
    "ledger is the feedback loop for refining their prompts/inputs (OpenBB data can be added as an input source next).",
):
    el.append(Paragraph(t, P))
el.append(Spacer(1, 8))
el.append(Paragraph("Not modeled: open-trade drawdown vs the trailing limit, news days, eval fees/resets, slippage beyond 1 tick. "
                    "Past results do not guarantee future results.", S))
doc.build(el)
print("ok", sys.argv[2])
