import { band, calendarWeeks, groupSkips, meters, signedUsd, skipLabel, skipRows, skipStrategy } from "./insights";

// every skip / reject reason code the backend can emit (grep of backend/app: Skip(...), skip_reason, AccountResult reasons)
const BACKEND_SKIP_CODES = `ACCOUNT_NOT_READY ACCOUNT_PAUSED ADVISORY_NO_AGREEMENT ADVISOR_DISAGREE AGGREGATE_RISK_EXCEEDS_LIMITS AI_DISAGREE AI_MISSING AI_NEUTRAL AI_NOT_STRONG AI_TA_MISSING AI_VT_MISSING ATTESTATION_MISSING BIAS_NO_TRADE BIG_OPEN BRUNI_NO_BARS C1_SWEPT C1_TOO_SMALL CALENDAR_MISSING CONSECUTIVE_LOSSES CONSISTENCY_CAP CONSISTENCY_DAY_STOP COOLDOWN CORB_NO_BARS CORB_NO_RANGE CUSHION_MAX_TRADES CUSHION_STOP DAY_STOP DEAD_ZONE DLL_LIMIT DRAWDOWN_TOO_DEEP FAST_EVAL_QUALITY_DAY FEED_DELAYED FEED_GAP FEED_LOST FEED_STALE GALA_NEWS_FIRST_HOUR GALA_NO_BARS GALA_NO_LEVEL GALA_NO_OPEN GALA_NO_TREND HARD_FLAT HEDGE_LOCK INSTRUMENT_DISABLED LAST_MINUTES LATE_DAY_NOT_ACTIVE LONG_ONLY MAX_TRADES MODEL_ALREADY_TRADED MODEL_FAILED MODEL_NOT_CONFIRMED MODE_OFF NEAR_MLL NEWS_BLACKOUT NEUTRAL_SCORE_LOW NOT_A_PLUS NO_HISTORY NO_TRADE OF_AMT_BALANCE OF_AMT_COUNTER_CONTEXT OF_AMT_NO_CONTEXT OF_AMT_NO_LEVEL OF_BAD_PRICE OF_CASPER_BUNCHED OF_CASPER_CONDITION OF_CASPER_CVD OF_CASPER_PRICE_CONFIRMS OF_CASPER_ROUND_STOP OF_CASPER_STACKED OF_COMPRESSION OF_DAILY_CAP OF_DELTA_ESTIMATED OF_ENVIRONMENT OF_LEVEL_WRONG_SIDE OF_LOCATION OF_NO_CONFIRM OF_PATH_EXHAUSTED OF_PATH_UNKNOWN OF_POSITION_OPEN OF_TA_ADVICE OF_TA_DISAGREES OF_UNKNOWN_SIGNAL OF_ZONE_DEAD_ZONE OF_ZONE_EVENT_SMALL OF_ZONE_EXCLUSIVE OF_ZONE_LAST_MINUTES OF_ZONE_MODE_OFF OF_ZONE_NOT_A_PLUS OF_ZONE_NOT_ENTRY OF_ZONE_NOT_PROVEN OF_ZONE_NO_EVENT OF_ZONE_NO_PRICE_CHANGE OF_ZONE_OPPOSING_EVENT OF_ZONE_PROGRAM_DAY OF_ZONE_REV_LEVEL OKALA_ADD_CAP OKALA_ADD_NOT_AT_BE OKALA_ADD_OPPOSITE OKALA_MAX_ADDS OPPOSING_DIVERGENCE OUTSIDE_WINDOW PAYOUT_PENDING POSITION_OPEN PROFILE_DISABLED PROGRAM_DAY RESEARCH_FAILED RESEARCH_NO_TRADE RISK_BASE_BELOW_PAUSE RR_BELOW_MIN RR_BELOW_MIN_AFTER_ROUNDING RR_INVALID_AFTER_FILL SCORE_BELOW_MIN SETUP_CONF_LOW SETUP_EXPIRED SETUP_INVALIDATED SETUP_LEVELS_INVALID SETUP_MALFORMED SETUP_ZONE_INVALID SHORT_ONLY SIGNAL_NOT_TRADEABLE SMALL_ROOM SPLIT_BUDGET_EXCEEDED STOP_INVALID STOP_TOO_TIGHT STOP_TOO_WIDE TARGET_TOO_CLOSE TREND_AGAINST WAIT_FOR_LARGER WORST_CASE_EXCEEDS_LIMITS WOULD_BREAK_BUFFER`.split(" ");

describe("skip labels", () => {
  it("maps known codes and passes unknown through", () => {
    expect(skipLabel("RR_BELOW_MIN")).toBe("Reward:risk below minimum");
    expect(skipLabel("OUTSIDE_WINDOW")).toBe("Outside trading hours");
    expect(skipLabel("NEWS_BLACKOUT")).toBe("News blackout");
    expect(skipLabel("SOMETHING_NEW")).toBe("Something new"); // unknown codes still get readable words
  });
  it("has a plain label for ALL backend reason codes (never a raw code)", () => {
    for (const c of BACKEND_SKIP_CODES) {
      const l = skipLabel(c);
      expect(l, c).not.toBe(c);
      expect(l, c).not.toMatch(/_/);
      expect(l.length, c).toBeGreaterThan(5);
    }
    expect(skipLabel("CONSISTENCY_DAY_STOP")).toBe("Consistency day stop reached — no new entries today");
    expect(skipLabel("LATE_DAY_NOT_ACTIVE")).toBe("Late-day option not active for this account");
    expect(skipLabel("OF_AMT_NO_CONTEXT")).toBe("AMT+ Order Flow filter: No context");
  });
  it("groups codes by strategy, biggest first, shared codes last", () => {
    expect(skipStrategy("OF_LOCATION")).toBe("Order Flow");
    expect(skipStrategy("RR_BELOW_MIN")).toBe("Confluence model");
    expect(skipStrategy("CONSISTENCY_DAY_STOP")).toBe("Any strategy");
    const g = groupSkips(skipRows({ CONSISTENCY_DAY_STOP: 9, OF_LOCATION: 2, OF_NO_CONFIRM: 1, RR_BELOW_MIN: 5 }, {}));
    expect(g.map((x) => [x.strategy, x.total])).toEqual([["Confluence model", 5], ["Order Flow", 3], ["Any strategy", 9]]);
  });
  it("sorts by count and attaches the average", () => {
    const rows = skipRows({ A: 1, RR_BELOW_MIN: 3 }, { RR_BELOW_MIN: 1.5 });
    expect(rows.map((r) => r.code)).toEqual(["RR_BELOW_MIN", "A"]);
    expect(rows[0]!.avg).toBe(1.5);
    expect(rows[1]!.avg).toBe(0);
  });
});

describe("bands", () => {
  it("switches at 50% and 80%", () => {
    expect(band(0.49)).toBe("safe");
    expect(band(0.5)).toBe("warn");
    expect(band(0.79)).toBe("warn");
    expect(band(0.8)).toBe("danger");
  });
});

describe("meters", () => {
  it("computes used fractions; consistency only for EVAL", () => {
    const m = meters({ stage: "EVAL", to_mll: "250", max_loss: "1000", dll_left: "300", dll_limit: "600",
      consistency_cap: "500", today_pnl: "400", idle_days: 2, idle_delete_days: 7 });
    expect(m.map((x) => x.key)).toEqual(["mll", "dll", "cons", "idle"]);
    expect(m[0]!.used).toBeCloseTo(0.75);
    expect(m[1]!.used).toBeCloseTo(0.5);
    expect(m[2]!.used).toBeCloseTo(0.8);
    expect(m[3]!.used).toBeCloseTo(2 / 7);
    const f = meters({ stage: "FUNDED", to_mll: "2000", max_loss: "1000", consistency_cap: "500" });
    expect(f.map((x) => x.key)).toEqual(["mll"]);
    expect(f[0]!.used).toBe(0); // clamped
  });
});

describe("calendar", () => {
  it("builds Monday-first weeks with totals", () => {
    const w = calendarWeeks([{ date: "2026-11-05", pnl: "290" }, { date: "2026-11-06", pnl: "-40.5" }, { date: "2026-11-09", pnl: "10" }]);
    expect(w).toHaveLength(2);
    expect(w[0]!.start).toBe("2026-11-02");
    expect(w[0]!.days[3]?.pnl).toBe("290");
    expect(w[0]!.days[0]).toBeNull();
    expect(w[0]!.total).toBeCloseTo(249.5);
    expect(w[1]!.start).toBe("2026-11-09");
  });
  it("formats signed money with arrows", () => {
    expect(signedUsd(5)).toBe("▲ +$5.00");
    expect(signedUsd(-5)).toBe("▼ −$5.00");
    expect(signedUsd(0)).toBe("$0.00");
  });
});
