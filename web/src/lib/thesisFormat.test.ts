import { describe, expect, it } from "vitest";

import {
  checkStatusLabel,
  formatCheckResult,
  formatCheckValue,
  formatFrameworkScore,
} from "./thesisFormat";
import type { FrameworkCheck } from "./types";

function check(overrides: Partial<FrameworkCheck>): FrameworkCheck {
  return {
    name: "Check",
    status: "pass",
    value: null,
    rating: "",
    points: 100,
    weight: 10,
    inputs: [],
    detail: "",
    ...overrides,
  };
}

describe("formatFrameworkScore", () => {
  it("renders dash for null (insufficient data)", () => {
    expect(formatFrameworkScore(null)).toBe("—");
  });
  it("rounds to whole number", () => {
    expect(formatFrameworkScore(91.4)).toBe("91");
    expect(formatFrameworkScore(37.5)).toBe("38");
  });
});

describe("checkStatusLabel", () => {
  it("maps statuses", () => {
    expect(checkStatusLabel("pass")).toBe("PASS");
    expect(checkStatusLabel("fail")).toBe("FAIL");
    expect(checkStatusLabel("unknown")).toBe("—");
  });
});

describe("formatCheckResult", () => {
  it("unknown → dash regardless of value", () => {
    expect(formatCheckResult(check({ status: "unknown", value: 2.5 }))).toBe("—");
  });
  it("prefers graded rating", () => {
    expect(
      formatCheckResult(check({ rating: "Excellent — 34%", value: 0.34 })),
    ).toBe("Excellent — 34%");
  });
  it("value + status when numeric", () => {
    expect(formatCheckResult(check({ value: 2.8 }))).toBe("2.80 — PASS");
  });
  it("status alone when no value", () => {
    expect(formatCheckResult(check({ status: "fail" }))).toBe("FAIL");
  });
});

describe("formatCheckValue", () => {
  it("abbreviates money scales", () => {
    expect(formatCheckValue(48_000_000_000)).toBe("48.0B");
    expect(formatCheckValue(1_500_000)).toBe("1.5M");
    expect(formatCheckValue(2_300_000_000_000)).toBe("2.3T");
  });
  it("keeps ratios readable", () => {
    expect(formatCheckValue(2.8)).toBe("2.80");
    expect(formatCheckValue(150)).toBe("150");
  });
});
