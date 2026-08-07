import { describe, expect, it } from "vitest";

import {
  checkStatusLabel,
  formatAdvisorConclusion,
  formatAdvisorConfidence,
  formatAssetVerdict,
  formatCheckResult,
  formatCheckValue,
  formatDifferencePct,
  formatFrameworkScore,
  formatMoney,
  formatMosStars,
  formatOsRating,
  formatThesisVerdict,
  formatValuationValue,
} from "./thesisFormat";
import type {
  AdvisorConclusion,
  FrameworkCheck,
  ThesisVerdict,
  ValuationMethod,
} from "./types";

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

function method(overrides: Partial<ValuationMethod>): ValuationMethod {
  return {
    id: "x",
    label: "X",
    school: "graham",
    value: null,
    unit: "currency",
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

describe("formatMoney", () => {
  it("null → dash", () => {
    expect(formatMoney(null)).toBe("—");
  });
  it("abbreviates", () => {
    expect(formatMoney(61_000_000_000)).toBe("61.0B");
  });
});

describe("formatValuationValue", () => {
  it("null → dash", () => {
    expect(formatValuationValue(method({}))).toBe("—");
  });
  it("percent as %", () => {
    expect(
      formatValuationValue(method({ value: 0.29, unit: "percent" })),
    ).toBe("29.0%");
  });
  it("ratio 2dp", () => {
    expect(
      formatValuationValue(method({ value: 1.5, unit: "ratio" })),
    ).toBe("1.50");
  });
});

describe("formatMosStars", () => {
  it("null → dash", () => {
    expect(formatMosStars(null)).toBe("—");
  });
  it("fills then empties", () => {
    expect(formatMosStars(5)).toBe("★★★★★");
    expect(formatMosStars(3)).toBe("★★★☆☆");
    expect(formatMosStars(1)).toBe("★☆☆☆☆");
  });
});

describe("formatAssetVerdict", () => {
  it("maps closed set", () => {
    expect(formatAssetVerdict("possible_undervaluation")).toBe(
      "Possible Undervaluation",
    );
    expect(formatAssetVerdict("fair")).toBe("Fair");
    expect(formatAssetVerdict(null)).toBe("—");
  });
});

describe("formatDifferencePct", () => {
  it("formats signed percent", () => {
    expect(formatDifferencePct(-0.213)).toBe("-21%");
    expect(formatDifferencePct(0.1)).toBe("+10%");
    expect(formatDifferencePct(null)).toBe("—");
  });
});

describe("formatThesisVerdict", () => {
  it("maps closed set", () => {
    const cases: [ThesisVerdict, string][] = [
      ["no_change", "No change"],
      ["strengthened", "Strengthened"],
      ["slightly_weaker", "Slightly weaker"],
      ["broken", "Broken"],
    ];
    for (const [v, label] of cases) {
      expect(formatThesisVerdict(v)).toBe(label);
    }
    expect(formatThesisVerdict(null)).toBe("—");
  });
});

describe("formatAdvisorConclusion", () => {
  it("maps closed directive set", () => {
    const cases: [AdvisorConclusion, string][] = [
      ["buy_more", "Buy more"],
      ["hold", "Hold"],
      ["trim", "Trim"],
      ["research_further", "Research further"],
      ["wait", "Wait for better entry"],
    ];
    for (const [v, label] of cases) {
      expect(formatAdvisorConclusion(v)).toBe(label);
    }
    expect(formatAdvisorConclusion(null)).toBe("—");
  });
});

describe("formatAdvisorConfidence", () => {
  it("formats percent", () => {
    expect(formatAdvisorConfidence(0.89)).toBe("89%");
    expect(formatAdvisorConfidence(null)).toBe("—");
  });
});

describe("formatOsRating", () => {
  it("passthrough or dash", () => {
    expect(formatOsRating("Excellent")).toBe("Excellent");
    expect(formatOsRating("")).toBe("—");
    expect(formatOsRating(null)).toBe("—");
  });
});
