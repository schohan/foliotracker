/** Format equal-weight fraction as a whole percent (0.333 → "33%"). */
export function formatWeightPercent(weight: number | null | undefined): string {
  if (weight == null || Number.isNaN(weight)) return "—";
  return `${Math.round(weight * 100)}%`;
}

/** Glanceable risk score; null stays honest. */
export function formatRiskScore(score: number | null | undefined): string {
  if (score == null || Number.isNaN(score)) return "—";
  return String(Math.round(score));
}

/** Pearson correlation to two decimals (−1.00 … 1.00); null stays honest. */
export function formatCorrelation(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "—";
  const clamped = Math.max(-1, Math.min(1, value));
  const sign = clamped > 0 ? "+" : "";
  return `${sign}${clamped.toFixed(2)}`;
}
