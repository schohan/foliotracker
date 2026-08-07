import { describe, expect, it } from "vitest";
import {
  matchesHealthBucket,
  tickersForHealthBucket,
  type PortfolioHealthBucket,
} from "./portfolioHealth";
import type {
  FrameworkScorecard,
  ThesisTicker,
} from "./types";

function card(
  overrides: Partial<FrameworkScorecard> & Pick<FrameworkScorecard, "framework">,
): FrameworkScorecard {
  return {
    label:
      overrides.framework === "graham"
        ? "Graham Deep Value"
        : "Financial Strength",
    score: 50,
    checks: [],
    coverage: 80,
    ...overrides,
  };
}

function ticker(overrides: Partial<ThesisTicker> = {}): ThesisTicker {
  return {
    ticker: "AAA",
    list_kind: "held",
    name: "Aaa Co",
    sector: "Tech",
    frameworks: [
      card({ framework: "graham", score: 60 }),
      card({ framework: "financial_strength", score: 80 }),
    ],
    valuation: null,
    margin_of_safety: {
      intrinsic_value: 100,
      market_price: 70,
      margin_of_safety: 0.3,
      stars: 4,
      rating: "Attractive",
      detail: "",
    },
    assets: null,
    monitoring: null,
    advisor: null,
    os_score: {
      score: 80,
      rating: "Good",
      coverage: 90,
      dimensions: [
        {
          id: "balance_sheet",
          label: "Balance Sheet",
          weight: 15,
          points: 75,
          detail: "",
        },
      ],
    },
    sources_used: ["yahoo"],
    gaps: [],
    ...overrides,
  };
}

describe("matchesHealthBucket", () => {
  it("flags strong balance sheets via FS or BS points", () => {
    expect(matchesHealthBucket(ticker(), "strong_balance_sheets")).toBe(true);
    expect(
      matchesHealthBucket(
        ticker({
          frameworks: [
            card({ framework: "graham", score: 60 }),
            card({ framework: "financial_strength", score: 30 }),
          ],
          os_score: {
            score: 40,
            rating: "Weak",
            coverage: 80,
            dimensions: [
              {
                id: "balance_sheet",
                label: "Balance Sheet",
                weight: 15,
                points: 20,
                detail: "",
              },
            ],
          },
        }),
        "strong_balance_sheets",
      ),
    ).toBe(false);
  });

  it("flags weak balance sheets", () => {
    const weak = ticker({
      frameworks: [
        card({ framework: "graham", score: 40 }),
        card({ framework: "financial_strength", score: 25 }),
      ],
      os_score: {
        score: 30,
        rating: "Weak",
        coverage: 70,
        dimensions: [
          {
            id: "balance_sheet",
            label: "Balance Sheet",
            weight: 15,
            points: 20,
            detail: "",
          },
        ],
      },
      margin_of_safety: null,
    });
    expect(matchesHealthBucket(weak, "weak_balance_sheets")).toBe(true);
  });

  it("flags value traps, undervalued, overvalued, conviction, broken", () => {
    const trap = ticker({
      frameworks: [
        card({ framework: "graham", score: 40 }),
        card({ framework: "financial_strength", score: 65 }),
      ],
      margin_of_safety: {
        intrinsic_value: 50,
        market_price: 80,
        margin_of_safety: -0.2,
        stars: 1,
        rating: "Poor",
        detail: "",
      },
    });
    expect(matchesHealthBucket(trap, "potential_value_traps")).toBe(true);
    expect(matchesHealthBucket(trap, "overvalued")).toBe(true);

    const cheap = ticker();
    expect(matchesHealthBucket(cheap, "significantly_undervalued")).toBe(true);
    expect(matchesHealthBucket(cheap, "high_conviction")).toBe(true);

    const broken = ticker({
      monitoring: {
        original_thesis: "x",
        current: {
          verdict: "broken",
          as_of: "2026-08-07T00:00:00Z",
          evidence: [],
          narrative: "",
          insight_mode: "deterministic",
        },
        timeline: [],
      },
    });
    expect(matchesHealthBucket(broken, "thesis_broken")).toBe(true);
  });
});

describe("tickersForHealthBucket", () => {
  it("filters the matching set", () => {
    const rows = [
      ticker({ ticker: "STRONG" }),
      ticker({
        ticker: "WEAK",
        frameworks: [
          card({ framework: "graham", score: 20 }),
          card({ framework: "financial_strength", score: 20 }),
        ],
        os_score: {
          score: 20,
          rating: "Poor",
          coverage: 60,
          dimensions: [
            {
              id: "balance_sheet",
              label: "Balance Sheet",
              weight: 15,
              points: 15,
              detail: "",
            },
          ],
        },
        margin_of_safety: null,
      }),
    ];
    const bucket: PortfolioHealthBucket = "strong_balance_sheets";
    expect(tickersForHealthBucket(rows, bucket).map((t) => t.ticker)).toEqual([
      "STRONG",
    ]);
  });
});
