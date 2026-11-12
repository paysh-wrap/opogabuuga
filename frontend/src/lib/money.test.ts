import { money } from "./money";

test("money: 2 decimals whenever there are cents, none for whole dollars (B8)", () => {
  expect(money("437.5")).toMatch(/^\$437\.50$/);
  expect(money("25000")).toBe(`$${(25000).toLocaleString()}`);
  expect(money(-12.3)).toMatch(/^-\$12\.30$/);
  expect(money(null)).toBe("—");
  expect(money("abc")).toBe("—");
});
