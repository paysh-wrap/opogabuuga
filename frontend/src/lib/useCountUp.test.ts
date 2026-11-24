import { renderHook } from "@testing-library/react";
import { expect, test } from "vitest";
import { useCountUp } from "./useCountUp";

test("first render returns the target exactly", () => {
  const { result } = renderHook(() => useCountUp(1234.5));
  expect(result.current).toBe(1234.5);
});

test("a NaN start value never renders NaN: falls back to the target", async () => {
  window.matchMedia = (() => ({ matches: false })) as unknown as typeof window.matchMedia;
  const seen: number[] = [];
  const { result, rerender } = renderHook(({ t }) => { const v = useCountUp(t); seen.push(v); return v; }, { initialProps: { t: NaN } });
  rerender({ t: 100 });
  await new Promise((r) => setTimeout(r, 50));
  expect(seen.slice(1).every((x) => Number.isFinite(x))).toBe(true);
  expect(Number.isFinite(result.current)).toBe(true);
});
