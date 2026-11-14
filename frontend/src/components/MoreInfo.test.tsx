import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import MoreInfo from "./MoreInfo";

test("long text starts folded, stays in the page and opens with the More info button", async () => {
  render(<MoreInfo testId="m"><p>Study: 2019–2026, PF 1.58</p></MoreInfo>);
  const box = screen.getByTestId("m");
  expect(box).not.toHaveAttribute("open"); // folded by default
  expect(box).toHaveTextContent("Study: 2019–2026, PF 1.58"); // never removed
  await userEvent.click(screen.getByText("More info"));
  expect(box).toHaveAttribute("open");
  await userEvent.click(screen.getByText("More info"));
  expect(box).not.toHaveAttribute("open");
});
