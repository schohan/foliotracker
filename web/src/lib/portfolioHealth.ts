/**
 * Portfolio health bucket matching — mirrors
 * app/services/thesis_os_score.py::build_portfolio_rollup thresholds.
 */

import type { ThesisTicker } from "./types";

export type PortfolioHealthBucket =
  | "strong_balance_sheets"
  | "weak_balance_sheets"
  | "potential_value_traps"
  | "significantly_undervalued"
  | "overvalued"
  | "high_conviction"
  | "thesis_broken";

export interface PortfolioHealthBucketMeta {
  key: PortfolioHealthBucket;
  label: string;
  /** Short investor explanation for the filter chip. */
  explain: string;
}

/** Locked thresholds from thesis_os_score.py */
const BS_STRONG = 70;
const BS_WEAK = 40;
const HIGH_CONVICTION = 75;
const VALUE_TRAP_FS = 60;
const UNDERVALUED_MOS = 0.3;

export const PORTFOLIO_HEALTH_BUCKETS: PortfolioHealthBucketMeta[] = [
  {
    key: "strong_balance_sheets",
    label: "Strong Balance Sheets",
    explain:
      "Companies that look financially sturdy — high liquidity / low leverage signals (balance-sheet points or Financial Strength ≥ 70).",
  },
  {
    key: "weak_balance_sheets",
    label: "Weak Balance Sheets",
    explain:
      "Companies with thinner cushions — balance-sheet points or Financial Strength below 40.",
  },
  {
    key: "potential_value_traps",
    label: "Potential Value Traps",
    explain:
      "Looks cheap on price but the business may be weak: negative Margin of Safety while Financial Strength is still ≥ 60.",
  },
  {
    key: "significantly_undervalued",
    label: "Significantly Undervalued",
    explain:
      "Price looks meaningfully below estimated worth: Margin of Safety ≥ 30%, or Net Asset Intelligence says possible undervaluation.",
  },
  {
    key: "overvalued",
    label: "Overvalued",
    explain:
      "Price looks rich versus estimated worth: negative Margin of Safety, or Net Asset Intelligence says possible overvaluation.",
  },
  {
    key: "high_conviction",
    label: "High Conviction",
    explain:
      "Investment OS Score ≥ 75 — several engines agree this name is relatively strong on the composite.",
  },
  {
    key: "thesis_broken",
    label: "Thesis Broken",
    explain:
      "Thesis Monitoring marked the story Broken — the investment case may no longer hold.",
  },
];

function fsScore(row: ThesisTicker): number | null {
  return (
    row.frameworks.find((f) => f.framework === "financial_strength")?.score ??
    null
  );
}

function balanceSheetPoints(row: ThesisTicker): number | null {
  const dim = row.os_score?.dimensions.find((d) => d.id === "balance_sheet");
  return dim?.points ?? null;
}

function mos(row: ThesisTicker): number | null {
  return row.margin_of_safety?.margin_of_safety ?? null;
}

/** Whether a ticker belongs in a portfolio-health count bucket. */
export function matchesHealthBucket(
  row: ThesisTicker,
  bucket: PortfolioHealthBucket,
): boolean {
  const bs = balanceSheetPoints(row);
  const fs = fsScore(row);
  const margin = mos(row);
  const assets = row.assets;

  switch (bucket) {
    case "strong_balance_sheets":
      return (
        (bs != null && bs >= BS_STRONG) || (fs != null && fs >= BS_STRONG)
      );
    case "weak_balance_sheets":
      return (bs != null && bs < BS_WEAK) || (fs != null && fs < BS_WEAK);
    case "potential_value_traps":
      return (
        margin != null &&
        margin < 0 &&
        fs != null &&
        fs >= VALUE_TRAP_FS
      );
    case "significantly_undervalued":
      return (
        (margin != null && margin >= UNDERVALUED_MOS) ||
        assets?.verdict === "possible_undervaluation"
      );
    case "overvalued":
      return (
        (margin != null && margin < 0) ||
        assets?.verdict === "possible_overvaluation"
      );
    case "high_conviction": {
      const score = row.os_score?.score;
      return score != null && score >= HIGH_CONVICTION;
    }
    case "thesis_broken":
      return row.monitoring?.current?.verdict === "broken";
    default:
      return false;
  }
}

export function tickersForHealthBucket(
  tickers: ThesisTicker[],
  bucket: PortfolioHealthBucket,
): ThesisTicker[] {
  return tickers.filter((t) => matchesHealthBucket(t, bucket));
}

export function healthBucketMeta(
  key: PortfolioHealthBucket,
): PortfolioHealthBucketMeta {
  return (
    PORTFOLIO_HEALTH_BUCKETS.find((b) => b.key === key) ??
    PORTFOLIO_HEALTH_BUCKETS[0]
  );
}
