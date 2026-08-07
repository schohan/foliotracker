import type { CheckStatus, FrameworkCheck } from "./types";

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
