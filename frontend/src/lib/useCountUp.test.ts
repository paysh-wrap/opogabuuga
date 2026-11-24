import { renderHook } from "@testing-library/react";
import { expect, test } from "vitest";
import { useCountUp } from "./useCountUp";

test("first render returns the target exactly", () => {
  const { result } = renderHook(() => useCountUp(1234.5));
  expect(result.current).toBe(1234.5);
});
