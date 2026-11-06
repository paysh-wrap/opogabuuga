import { band, calendarWeeks, meters, signedUsd, skipLabel, skipRows } from "./insights";

describe("skip labels", () => {
  it("maps known codes and passes unknown through", () => {
    expect(skipLabel("RR_BELOW_MIN")).toBe("Reward:risk below minimum");
    expect(skipLabel("OUTSIDE_WINDOW")).toBe("Outside trading hours");
    expect(skipLabel("NEWS_BLACKOUT")).toBe("News blackout");
    expect(skipLabel("SOMETHING_NEW")).toBe("SOMETHING_NEW");
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
