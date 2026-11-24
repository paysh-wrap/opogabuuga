import { badge, contrast, mission, theme } from "./theme";
// @ts-expect-error -- tailwind.config.js is plain JS without types
import tw from "../../tailwind.config.js";

// §18/§21: WCAG AA contrast for every text color on every surface.
test.each([
  ["gold", theme.gold], ["goldLight", theme.goldLight], ["blue", theme.blue], ["blueLight", theme.blueLight],
])("%s passes AA (4.5:1) on bg and card", (_n, fg) => {
  expect(contrast(fg, theme.bg)).toBeGreaterThanOrEqual(4.5);
  expect(contrast(fg, theme.card)).toBeGreaterThanOrEqual(4.5);
});

// Inputs use a darker field (#0A1020-ish) and the border colour sits behind thin text in chips.
test.each([["gold", theme.gold], ["goldLight", theme.goldLight], ["blue", theme.blue], ["blueLight", theme.blueLight]])(
  "%s passes AA on input fields", (_n, fg) => expect(contrast(fg, "#070C19")).toBeGreaterThanOrEqual(4.5));

test.each([["gold", theme.gold], ["goldLight", theme.goldLight], ["blueLight", theme.blueLight]])(
  "%s (P&L calendar text) passes AA on the strongest gold and blue cell tints (alpha 0.25)", (_n, fg) => {
    expect(contrast(fg, "#424034")).toBeGreaterThanOrEqual(4.5); // 0.25 × gold over card
    expect(contrast(fg, "#1C3464")).toBeGreaterThanOrEqual(4.5); // 0.25 × blue over card
  });

test("red/green badges are icons only but still reach 3:1 non-text contrast (WCAG 1.4.11)", () => {
  for (const c of Object.values(badge)) {
    expect(contrast(c, theme.bg)).toBeGreaterThanOrEqual(3);
    expect(contrast(c, theme.card)).toBeGreaterThanOrEqual(3);
  }
});

test("Tailwind palette matches theme.ts exactly (font colours blue/gold only)", () => {
  const c = (tw as { theme: { extend: { colors: Record<string, string> } } }).theme.extend.colors;
  for (const k of ["gold", "goldLight", "blue", "blueLight"] as const) expect(c[k]?.toUpperCase()).toBe(theme[k]);
});

test("D93 mandatory highlight is gold-family, passes AA on every surface and matches Tailwind", () => {
  for (const bg of [theme.bg, theme.card, mission.bg, mission.tile, mission.tile2, "#070C19"])
    expect(contrast(theme.mandatory, bg)).toBeGreaterThanOrEqual(4.5);
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(theme.mandatory.slice(i, i + 2), 16)) as [number, number, number];
  expect(r).toBeGreaterThan(g); expect(g).toBeGreaterThan(b); // warm yellow-gold, never red/green
  const c = (tw as { theme: { extend: { colors: Record<string, string> } } }).theme.extend.colors;
  expect(c.mandatory?.toUpperCase()).toBe(theme.mandatory);
});

test("D93 mission text colours pass AA on mission tiles", () => {
  for (const fg of [theme.gold, theme.goldLight, theme.blue, theme.blueLight])
    for (const bg of [mission.bg, mission.tile, mission.tile2]) expect(contrast(fg, bg)).toBeGreaterThanOrEqual(4.5);
});

// UI review 2026-11-24: tinted surfaces (blue/14 outline button ≈ #11224C, gold/10 pick button ≈ #1E2231, mission.navOn).
// Plain `blue` fails AA on these, so labels on tints use blueLight and secondary prose uses blueLight at 78 %.
const TINTS = ["#11224C", "#1E2231", mission.navOn] as const;
test.each([["gold", theme.gold], ["goldLight", theme.goldLight], ["blueLight", theme.blueLight]])(
  "%s (button/label text) passes AA on every tinted button surface", (_n, fg) => {
    for (const bg of TINTS) expect(contrast(fg, bg)).toBeGreaterThanOrEqual(4.5);
  });

test("plain blue is NOT used as text on tints (it fails AA there, so CSS maps it to blueLight)", () => {
  expect(Math.min(...TINTS.map((bg) => contrast(theme.blue, bg)))).toBeLessThan(4.5);
});

function mix(fg: string, bg: string, a: number): string {
  const h = (s: string, i: number) => parseInt(s.slice(i, i + 2), 16);
  return "#" + [1, 3, 5].map((i) => Math.round(h(fg, i) * a + h(bg, i) * (1 - a)).toString(16).padStart(2, "0")).join("");
}
test("secondary text = blueLight at 78 % passes AA on cards, tiles and the Neon card", () => {
  for (const bg of [theme.bg, theme.card, mission.tile, mission.tile2, "#0A1230", "#11224C"])
    expect(contrast(mix(theme.blueLight, bg, theme.secondaryAlpha), bg)).toBeGreaterThanOrEqual(4.5);
});
