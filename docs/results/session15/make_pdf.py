"""Build Paytience_best_strategy_lucid.pdf from out/recommend.json (written by report.py) - causal numbers only.
Successor of docs/results/session10/make_pdf.py (same reportlab look).  usage: python3 make_pdf.py"""
import json, os
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

HERE = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(f"{HERE}/out/recommend.json"))
NAVY, BLUE, GOLD, GREY = colors.HexColor("#0A1020"), colors.HexColor("#1D4ED8"), colors.HexColor("#B8860B"), colors.HexColor("#E5E7EB")
ss = getSampleStyleSheet()
H1 = ParagraphStyle("h1", parent=ss["Title"], textColor=NAVY, fontSize=19, spaceAfter=6)
H2 = ParagraphStyle("h2", parent=ss["Heading2"], textColor=BLUE, spaceBefore=10, spaceAfter=4)
P = ParagraphStyle("p", parent=ss["BodyText"], fontSize=9.5, leading=13)
S = ParagraphStyle("s", parent=P, fontSize=8, leading=10.5, textColor=colors.HexColor("#374151"))
C = ParagraphStyle("c", parent=P, fontSize=7.6, leading=9.5)
HDR = ParagraphStyle("hdr", parent=ss["BodyText"], fontSize=7, leading=8.5, textColor=colors.white, fontName="Helvetica-Bold")
m = lambda v: f"${v:,.0f}"  # noqa: E731
p = lambda v: f"{v:.0f}%"  # noqa: E731


def table(header, body, widths, hi=()):
    t = Table([[Paragraph(h, HDR) for h in header]] + [[Paragraph(str(x), C) for x in row] for row in body], colWidths=[w * inch for w in widths], repeatRows=1)
    st = [("BACKGROUND", (0, 0), (-1, 0), NAVY), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
          ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GREY]), ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#9CA3AF"))]
    for i in hi: st += [("BOX", (0, i), (-1, i), 1.2, GOLD)]
    t.setStyle(TableStyle(st))
    return t


def row(plan, label, size, r, ok):
    i, h = r["IS"], r["HO"]
    return [f"<b>Pro {plan}</b><br/>{label}", size, f"{p(i['eb']['pass_'])} / <b>{p(h['eb']['pass_'])}</b>", f"{p(i['eb']['bust'])} / <b>{p(h['eb']['bust'])}</b>",
            f"{h['eb']['med']:.0f} sessions", f"{p(i['fb']['bust'])} / <b>{p(h['fb']['bust'])}</b>", f"{m(i['fb']['per2w'])} / <b>{m(h['fb']['per2w'])}</b>",
            f"{m(5 * i['fb']['per2w'])} / <b>{m(5 * h['fb']['per2w'])}</b>", ok]


HEAD = ["Plan", "Size", "Eval pass<br/>2021-23 / <b>2024-26</b>", "Eval bust<br/>2021-23 / <b>2024-26</b>", "Typical time to pass (2024-26)",
        "Funded bust year 1<br/>2021-23 / <b>2024-26</b>", "Income per 2 weeks, 1 account", "Income per 2 weeks, 5 accounts", "Meets limits?"]
W = [0.85, 1.35, 0.8, 0.8, 0.75, 0.9, 0.8, 0.85, 0.55]
rec = [row(k, "recommended", v["size"], v["rec"], "<b>NO</b>" if k == "25K" else "yes") for k, v in R.items()]
MLL = {"25K": 1000, "50K": 2000, "100K": 3000, "150K": 4500}
cz = lambda k, c: f"{c['q']}" + (f" ({c['brake'][1]} under ${c['brake'][0] * MLL[k]:,.0f})" if "brake" in c else "")  # noqa: E731
live = [row(k, "today", f"eval {cz(k, v['live']['ecfg'])}; funded {cz(k, v['live']['fcfg'])} micros", v["live"], "NO") for k, v in R.items()]
thin = [row(k, "most income under 35%", v["thin_size"], v["thin"], "yes (thin)") for k, v in R.items() if v["thin"] and v["thin_size"] != v["size"]]
year = [[f"Pro {k}", m(v["rec"]["IS"]["fb"]["year"]), m(v["rec"]["HO"]["fb"]["year"]), m(v["rec"]["HO"]["fb"]["year_median"]), p(v["rec"]["HO"]["fb"]["any_pay"]),
         m(5 * v["rec"]["HO"]["fb"]["year"]), f"{v['rec']['HO']['eb']['med']:.0f} / {v['rec']['HO']['eb']['p80']:.0f}"] for k, v in R.items()]
b = R["150K"]["rec"]["HO"]; t0 = R["150K"]["live"]["HO"]

doc = SimpleDocTemplate(f"{HERE}/Paytience_best_strategy_lucid.pdf", pagesize=letter, leftMargin=0.45 * inch, rightMargin=0.45 * inch, topMargin=0.5 * inch,
                        bottomMargin=0.5 * inch, title="Paytience - best strategy for Lucid Pro accounts (causal numbers)")
el = [Paragraph("Paytience — best strategy for Lucid Pro accounts", H1),
      Paragraph("Session 15 research, 2026-11-10. Causal (no look-ahead), real costs (fees + 1 tick slippage per side), picked on 2021-11..2023-12 and judged on "
                "2024-01..2026-10, Databento 1-minute MNQ / MES / MGC, every Pro plan's own Lucid rules (EOD trailing loss limit, daily loss limit, 40% payout "
                "consistency, payout caps, 90% split, payout every 2 weeks). This replaces the old 2-week income breakdown, whose numbers used a rule that cannot be traded live.", P),
      Paragraph("The recommendation", H2),
      Paragraph(f"<b>Keep NOISE on MNQ, add the profit lock, switch the afternoon fade off, and trade smaller. Best plan: Pro 150K at 3 micros, dropping to 1 micro "
                f"while the cushion above the loss limit is under $2,250.</b> On the held-out years 2024-26: evaluation pass {p(b['eb']['pass_'])}, evaluation bust "
                f"{p(b['eb']['bust'])}, funded bust in year 1 {p(b['fb']['bust'])}, about {m(b['fb']['per2w'])} per 2 weeks per account "
                f"({m(5 * b['fb']['per2w'])} for 5 accounts). Today's setup on the same years: pass {p(t0['eb']['pass_'])}, eval bust {p(t0['eb']['bust'])}, "
                f"funded bust {p(t0['fb']['bust'])}, {m(t0['fb']['per2w'])} per 2 weeks.", P),
      Paragraph("• <b>Win rate: 48% (2021-23) / 52% (2024-26).</b> A 60-70% win rate is not reachable with a real edge: every idea with 55-61% wins lost money "
                "or needed targets below 1.5R (against your rule) and still lost.", P),
      Paragraph("• <b>A 60-70% evaluation pass rate is reachable on 50K, 100K and 150K (77-78%)</b> with bust well under 35% — but only at small size, so a typical "
                "evaluation takes 7 to 9 months and first-year income is modest.", P),
      Paragraph("• <b>Pro 25K cannot meet the limits</b> (one micro is too big for a $1,000 loss limit). Do not buy 25K accounts for this strategy.", P),
      Paragraph("• Nothing outside NOISE passed: 14 well-known ideas (VWAP reversion, opening-range fade and breakout, gap fill, gap-and-go, prior-day and pre-market "
                "sweeps, trend-day pullback, NR7 breakout, gold overnight reversion) on MNQ, MES and MGC all failed the pick period or the held-out period.", P),
      Paragraph("Recommended setup per plan — NOISE + profit lock (MNQ)", H2), table(HEAD, rec, W, hi=(4,)),
      Paragraph("Bold = held-out 2024-26 (plan on these). Five accounts take the same trades: they pay together and bust together. Income is before evaluation fees.", S),
      Paragraph("Today's setup for comparison — NOISE alone at the live size table", H2), table(HEAD, live, W),
      Paragraph("More income, thinner margin (still under 35% bust)", H2), table(HEAD, thin, W),
      Paragraph("First funded year in dollars (recommended setup)", H2),
      table(["Plan", "Average, 1 account, 2021-23", "Average, 1 account, 2024-26", "Middle outcome, 1 account, 2024-26", "Accounts with at least one payout (2024-26)",
             "Average, 5 accounts, 2024-26", "Sessions to pass the eval: typical / slow 1-in-5 (2024-26)"], year, [0.8, 1.15, 1.15, 1.15, 1.2, 1.1, 1.3]),
      Paragraph("What Paytience would trade", H2)]
for t in (
    "<b>NOISE</b> — intraday momentum on MNQ (Zarattini, Aziz &amp; Barbon 2024): hourly checks 10:00–15:00 ET; enter when price closes outside the 14-day noise band; "
    "exit when the hourly close crosses back through the band / VWAP; flat 16:00; max 3 a day; $250 emergency stop per micro.",
    "<b>Profit lock (new, proposal D75-P1)</b> — once a trade is 100 points in profit the stop moves to entry + 10 points; if that stop is hit, NOISE is done for the "
    "day. Same total profit, win rate 44% → 52%, much smaller swings. It is a stop move, not a target, but the average winner gets smaller (1.27× the average loser, "
    "was 1.65×).",
    "<b>Afternoon fade: OFF</b> — it has no edge when traded the way the live app can trade it (session 14).",
    "<b>Size</b> — 50K: 1 micro. 100K: 2 micros, 1 while the cushion is under $2,100. 150K: 3 micros, 1 while the cushion is under $2,250. Same in the evaluation "
    "and funded stages. No High-risk or Evaluation-Mode boost.",
):
    el.append(Paragraph("• " + t, P))
el.append(Paragraph("The cost of staying safe", H2))
for t in (
    "In hard years (2024-26) safety is nearly free: on 150K every size from 3 to 4 micros pays $78–$94 per 2 weeks, because the bigger sizes lose accounts as fast "
    "as they earn. The recommended size pays $79 with an 11% funded bust instead of 31–53%.",
    "In easy years (2021-23) it costs income: 150K $174 per 2 weeks instead of $221 at 4 micros (−21%); 100K $126 instead of $178 (−29%); 50K $72 instead of $139 (−48%).",
    "The second cost is time: 7–9 months to pass an evaluation instead of 1.5–5 months at today's sizes (which bust about half the time).",
):
    el.append(Paragraph("• " + t, P))
el.append(Paragraph("Read this before relying on the numbers", H2))
for t in (
    "<b>Sizing was chosen knowing both periods.</b> Sizes that looked safe on 2021-23 alone failed in 2024-26 (150K at 4 micros: 22% eval bust became 45%), because "
    "the Nasdaq is ~68% higher and each micro now swings more dollars against the same Lucid limits. The recommended sizes keep bust at 25% or less in both periods "
    "(a 10-point margin). If the index rises another ~25%, sizes must be re-checked.",
    "Percentages come from 1,000 bootstrap paths built from 10-session blocks of real days, cross-checked against rolling real start dates. Read them as ± 5 points.",
    "Not modelled: evaluation / reset fees, news blackouts, slippage above 1 tick, any Lucid time or inactivity limit on evaluations (verify that a 7–9 month "
    "evaluation is allowed), the live app's stop-shrink / freeze logic.",
    "The live app does not have the profit lock yet and still uses the old size table. Nothing was changed in the app — these are proposals for your approval.",
    "Projection from past data, not a promise.",
):
    el.append(Paragraph("• " + t, P))
el.append(Spacer(1, 6))
el.append(Paragraph("Full tables, all failed ideas and the scripts: docs/results/session15/README.md", S))
doc.build(el)
print("ok")
