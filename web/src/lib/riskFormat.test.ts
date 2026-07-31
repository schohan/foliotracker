import { describe, expect, it } from "vitest";
import { formatRiskScore, formatWeightPercent } from "./riskFormat";

describe("formatWeightPercent", () => {
  it("rounds equal-weight thirds", () => {
    expect(formatWeightPercent(1 / 3)).toBe("33%");
  });
  it("handles full and empty", () => {
    expect(formatWeightPercent(1)).toBe("100%");
    expect(formatWeightPercent(null)).toBe("—");
  });
});

describe("formatRiskScore", () => {
  it("rounds and nulls", () => {
    expect(formatRiskScore(55.4)).toBe("55");
    expect(formatRiskScore(null)).toBe("—");
  });
});
