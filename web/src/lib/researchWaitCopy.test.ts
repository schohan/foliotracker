import { describe, expect, it } from "vitest";
import { RESEARCH_WAIT_LINE, researchWaitCopy } from "./researchWaitCopy";

describe("researchWaitCopy", () => {
  it("returns null when not refreshing", () => {
    expect(researchWaitCopy(false)).toBeNull();
  });

  it("returns the static honest line when refreshing", () => {
    expect(researchWaitCopy(true)).toBe(RESEARCH_WAIT_LINE);
    expect(researchWaitCopy(true)).toContain("Researching");
  });
});
