import { describe, expect, it } from "vitest";
import {
  buildDecisionMapRows,
  decisionSectionId,
  formatAdvisorAnswer,
  formatFrameworkAnswer,
  formatMonitoringAnswer,
  formatPortfolioMonitoringAnswer,
  formatPortfolioValuationAnswer,
  formatValuationAnswer,
} from "./decisionMap";
import type {
  FrameworkScorecard,
  PortfolioHealthRollup,
  ThesisTicker,
} from "./types";

function card(
  overrides: Partial<FrameworkScorecard> & Pick<FrameworkScorecard, "framework">,
): FrameworkScorecard {
  return {
    label: overrides.framework === "graham" ? "Graham Deep Value" : "Financial Strength",
    score: 70,
    checks: [],
    coverage: 1,
    ...overrides,
  };
}

function ticker(overrides: Partial<ThesisTicker> = {}): ThesisTicker {
  return {
    ticker: "NVDA",
    list_kind: "held",
    name: "NVIDIA",
    sector: "Technology",
    frameworks: [
      card({ framework: "graham", score: 72 }),
      card({ framework: "financial_strength", score: 81 }),
    ],
    valuation: null,
    margin_of_safety: {
      intrinsic_value: 100,
      market_price: 80,
      margin_of_safety: 0.2,
      stars: 3,
      rating: "Attractive",
      detail: "",
    },
    assets: null,
    monitoring: {
      original_thesis: "Quality compounder",
      current: {
        verdict: "strengthened",
        as_of: "2026-08-07T00:00:00Z",
        evidence: [],
        narrative: "",
        insight_mode: "deterministic",
      },
      timeline: [],
    },
    advisor: {
      reasoning: ["MoS intact"],
      conclusion: "hold",
      conclusion_label: "Hold",
      confidence: 0.72,
      provider: "deterministic",
    },
    os_score: null,
    sources_used: ["yahoo"],
    gaps: [],
    ...overrides,
  };
}

function portfolio(
  overrides: Partial<PortfolioHealthRollup> = {},
): PortfolioHealthRollup {
  return {
    health_score: 68,
    health_rating: "Good",
    tickers_scored: 4,
    strong_balance_sheets: 2,
    weak_balance_sheets: 1,
    potential_value_traps: 0,
    significantly_undervalued: 1,
    overvalued: 2,
    high_conviction: 1,
    thesis_broken: 0,
    ...overrides,
  };
}

describe("formatFrameworkAnswer", () => {
  it("joins short labels and scores", () => {
    expect(formatFrameworkAnswer(ticker())).toBe("Graham 72 · FS 81");
  });

  it("returns dash for empty", () => {
    expect(formatFrameworkAnswer(null)).toBe("—");
    expect(formatFrameworkAnswer(ticker({ frameworks: [] }))).toBe("—");
  });
});

describe("formatValuationAnswer", () => {
  it("joins stars and rating", () => {
    expect(formatValuationAnswer(ticker())).toBe("★★★☆☆ · Attractive");
  });

  it("returns dash without MoS", () => {
    expect(formatValuationAnswer(ticker({ margin_of_safety: null }))).toBe("—");
  });
});

describe("formatMonitoringAnswer / formatAdvisorAnswer", () => {
  it("formats verdict and advisor line", () => {
    expect(formatMonitoringAnswer(ticker())).toBe("Strengthened");
    expect(formatAdvisorAnswer(ticker())).toBe("Hold · 72%");
  });
});

describe("portfolio fallbacks", () => {
  it("summarizes valuation and monitoring counts", () => {
    expect(formatPortfolioValuationAnswer(portfolio())).toBe(
      "1 undervalued · 2 overvalued",
    );
    expect(formatPortfolioMonitoringAnswer(portfolio())).toBe(
      "No broken theses",
    );
    expect(
      formatPortfolioMonitoringAnswer(portfolio({ thesis_broken: 2 })),
    ).toBe("2 thesis broken");
  });
});

describe("buildDecisionMapRows", () => {
  it("uses ticker answers when selected", () => {
    const rows = buildDecisionMapRows(ticker(), portfolio());
    expect(rows.map((r) => r.id)).toEqual([
      "brief",
      "fundamentals",
      "frameworks",
      "valuation",
      "monitoring",
      "advisor",
    ]);
    expect(rows[0].answer).toBe("Open Brief");
    expect(rows[1].planned).toBe(true);
    expect(rows[1].answer).toBe("Planned");
    expect(rows[2].answer).toBe("Graham 72 · FS 81");
    expect(rows[3].answer).toContain("Attractive");
    expect(rows[4].answer).toBe("Strengthened");
    expect(rows[5].answer).toBe("Hold · 72%");
  });

  it("falls back to portfolio / select prompts without ticker", () => {
    const rows = buildDecisionMapRows(null, portfolio());
    expect(rows[2].answer).toBe("Select a ticker");
    expect(rows[2].needsTicker).toBe(true);
    expect(rows[3].answer).toBe("1 undervalued · 2 overvalued");
    expect(rows[4].answer).toBe("No broken theses");
    expect(rows[5].answer).toBe("Select a ticker");
  });
});

describe("decisionSectionId", () => {
  it("maps targets to heading ids", () => {
    expect(decisionSectionId("brief")).toBeNull();
    expect(decisionSectionId("frameworks")).toBe("frameworks-heading");
    expect(decisionSectionId("valuation")).toBe("valuation-heading");
  });
});
