import { etDateTime, etTime } from "./time";

test("times render in Eastern Time across DST", () => {
  expect(etTime("2026-11-05T15:00:00Z")).toBe("10:00:00 ET"); // EST
  expect(etTime("2026-07-06T14:30:00Z")).toBe("10:30:00 ET"); // EDT
  expect(etDateTime("2026-11-05T15:00:00Z")).toBe("Nov 5, 10:00 ET");
});
