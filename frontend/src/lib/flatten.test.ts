import { fmtCountdown, secondsToEt } from "./flatten";

test("countdown to 16:40 ET", () => {
  // 2026-11-05 15:00 UTC = 10:00 ET (EST)
  expect(secondsToEt("16:40", new Date("2026-11-05T15:00:00Z"))).toBe(6 * 3600 + 40 * 60);
  expect(secondsToEt("16:40", new Date("2026-11-05T22:00:00Z"))).toBeLessThan(0);
  expect(fmtCountdown(3725)).toBe("01:02:05");
  expect(fmtCountdown(-5)).toBe("00:00:00");
});
