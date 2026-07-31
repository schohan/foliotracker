import { describe, expect, it } from "vitest";
import {
  formatCorrelation,
  formatRiskScore,
  formatWeightPercent,
} from "./riskFormat";

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

describe("formatCorrelation", () => {
  it("formats signed two decimals", () => {
    expect(formatCorrelation(0.956)).toBe("+0.96");
    expect(formatCorrelation(-0.4)).toBe("-0.40");
    expect(formatCorrelation(0)).toBe("0.00");
  });
  it("nulls stay honest", () => {
    expect(formatCorrelation(null)).toBe("—");
  });
});
