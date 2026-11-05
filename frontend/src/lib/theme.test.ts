import { contrast, theme } from "./theme";

// §18/§21: WCAG AA contrast for every text color on every surface.
test.each([
  ["gold", theme.gold], ["goldLight", theme.goldLight], ["blue", theme.blue], ["blueLight", theme.blueLight],
])("%s passes AA (4.5:1) on bg and card", (_n, fg) => {
  expect(contrast(fg, theme.bg)).toBeGreaterThanOrEqual(4.5);
  expect(contrast(fg, theme.card)).toBeGreaterThanOrEqual(4.5);
});
