import type {
  AssetVerdict,
  AdvisorConclusion,
  CheckStatus,
  FrameworkCheck,
  ThesisTicker,
  ThesisVerdict,
  ValuationMethod,
  ValuationUnit,
} from "./types";

/** Honest coverage label for a thesis row (rate limits / thin fundamentals). */
export type ThesisCoverageKind = "ok" | "partial" | "thin";

export interface ThesisCoverage {
  kind: ThesisCoverageKind;
  /** Short table badge: ok / partial / thin. */
  label: string;
  /** Drawer / meta explanation — never invents values. */
  detail: string;
}

/**
 * Classify how much of a ticker's thesis engines have real data.
 * Thin rows (rate-limited / empty sources) stay selectable — UI must explain gaps.
 */
export function thesisRowCoverage(row: ThesisTicker): ThesisCoverage {
  const scored = row.frameworks.filter((f) => f.score != null).length;
  const totalFw = row.frameworks.length;
  const hasValuation =
    row.valuation != null ||
    row.margin_of_safety != null ||
    row.assets != null;
  const hasMonitoring = row.monitoring != null;
  const hasAdvisor = row.advisor != null;
  const sources = row.sources_used;
  const gapCount = row.gaps.length;
  const sourceLine =
    sources.length > 0 ? sources.join(", ") : "no fundamentals sources";

  if (scored === 0 && !hasValuation && !hasMonitoring && !hasAdvisor) {
    return {
      kind: "thin",
      label: "thin",
      detail:
        gapCount > 0
          ? `Limited data (${sourceLine}). ${gapCount} source gap${gapCount === 1 ? "" : "s"} — scores stay blank rather than invented.`
          : `Limited data (${sourceLine}). Not enough fields to score frameworks or valuation.`,
    };
  }

  if (scored < totalFw || gapCount > 0 || !hasValuation) {
    return {
      kind: "partial",
      label: "partial",
      detail: `Partial coverage · ${sourceLine}${gapCount > 0 ? ` · ${gapCount} gap${gapCount === 1 ? "" : "s"}` : ""}`,
    };
  }

  return {
    kind: "ok",
    label: "ok",
    detail: `Sources: ${sourceLine}`,
  };
}

/** Framework score 0–100 → "91" | "—" (null = insufficient data). */
export function formatFrameworkScore(score: number | null): string {
  if (score == null) return "—";
  return String(Math.round(score));
}

/** Check status → short table label. */
export function checkStatusLabel(status: CheckStatus): string {
  if (status === "pass") return "PASS";
  if (status === "fail") return "FAIL";
  return "—";
}

/**
 * One-cell check result, preferring the graded rating when present:
 * "Excellent — 34%" | "2.8 — PASS" | "PASS" | "—".
 */
export function formatCheckResult(check: FrameworkCheck): string {
  if (check.status === "unknown") return "—";
  if (check.rating) return check.rating;
  if (check.value != null) {
    return `${formatCheckValue(check.value)} — ${checkStatusLabel(check.status)}`;
  }
  return checkStatusLabel(check.status);
}

/** Compact numeric display: ratios 2dp, large money values abbreviated. */
export function formatCheckValue(value: number): string {
  const abs = Math.abs(value);
  if (abs >= 1e12) return `${(value / 1e12).toFixed(1)}T`;
  if (abs >= 1e9) return `${(value / 1e9).toFixed(1)}B`;
  if (abs >= 1e6) return `${(value / 1e6).toFixed(1)}M`;
  if (abs >= 100) return value.toFixed(0);
  return value.toFixed(2);
}

/** Money / null → abbreviated currency or "—". */
export function formatMoney(value: number | null): string {
  if (value == null) return "—";
  return formatCheckValue(value);
}

/** Valuation method value by unit (currency / ratio / multiple / percent). */
export function formatValuationValue(method: ValuationMethod): string {
  if (method.value == null) return "—";
  return formatByUnit(method.value, method.unit);
}

export function formatByUnit(value: number, unit: ValuationUnit): string {
  if (unit === "percent") {
    return `${(value * 100).toFixed(1)}%`;
  }
  if (unit === "ratio" || unit === "multiple") {
    return value.toFixed(2);
  }
  return formatCheckValue(value);
}

/** MoS stars 1–5 → "★★★★★" filled + "☆" empty; null → "—". */
export function formatMosStars(stars: number | null): string {
  if (stars == null || stars < 1) return "—";
  const n = Math.min(5, Math.max(1, Math.round(stars)));
  return "★".repeat(n) + "☆".repeat(5 - n);
}

/** Asset verdict enum → PRD display label. */
export function formatAssetVerdict(verdict: AssetVerdict | null): string {
  if (verdict == null) return "—";
  if (verdict === "possible_undervaluation") return "Possible Undervaluation";
  if (verdict === "possible_overvaluation") return "Possible Overvaluation";
  return "Fair";
}

/** Difference fraction → "−21%" | "—". */
export function formatDifferencePct(pct: number | null): string {
  if (pct == null) return "—";
  const signed = pct * 100;
  const rounded = Math.round(signed);
  if (rounded > 0) return `+${rounded}%`;
  return `${rounded}%`;
}

/** Closed thesis-change verdict → PRD label. */
export function formatThesisVerdict(verdict: ThesisVerdict | null | undefined): string {
  if (verdict == null) return "—";
  if (verdict === "no_change") return "No change";
  if (verdict === "strengthened") return "Strengthened";
  if (verdict === "slightly_weaker") return "Slightly weaker";
  if (verdict === "broken") return "Broken";
  return "—";
}

/** Advisor conclusion enum → PRD display label. */
export function formatAdvisorConclusion(
  conclusion: AdvisorConclusion | null | undefined,
): string {
  if (conclusion == null) return "—";
  if (conclusion === "buy_more") return "Buy more";
  if (conclusion === "hold") return "Hold";
  if (conclusion === "trim") return "Trim";
  if (conclusion === "research_further") return "Research further";
  if (conclusion === "wait") return "Wait for better entry";
  return "—";
}

/** Confidence 0–1 → "89%". */
export function formatAdvisorConfidence(confidence: number | null | undefined): string {
  if (confidence == null || Number.isNaN(confidence)) return "—";
  return `${Math.round(confidence * 100)}%`;
}

/** OS / portfolio health rating string → passthrough or "—". */
export function formatOsRating(rating: string | null | undefined): string {
  if (rating == null || rating.trim() === "") return "—";
  return rating;
}
