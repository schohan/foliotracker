import { describe, expect, it } from "vitest";
import { rowFocusId, shouldCloseOnEscape } from "./focusHelpers";

describe("shouldCloseOnEscape", () => {
  it("returns true for Escape", () => {
    expect(shouldCloseOnEscape("Escape")).toBe(true);
  });

  it("returns false for other keys", () => {
    expect(shouldCloseOnEscape("Enter")).toBe(false);
    expect(shouldCloseOnEscape("Tab")).toBe(false);
  });
});

describe("rowFocusId", () => {
  it("builds a stable focus id from ticker", () => {
    expect(rowFocusId("NVDA")).toBe("ticker-row-NVDA");
  });
});
