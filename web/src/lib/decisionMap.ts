import {
  formatAdvisorConclusion,
  formatAdvisorConfidence,
  formatFrameworkScore,
  formatMosStars,
  formatThesisVerdict,
} from "./thesisFormat";
import type {
  FrameworkId,
  PortfolioHealthRollup,
  ThesisTicker,
} from "./types";

/** Anchor / nav targets for the Decision Map strip. */
export type DecisionMapTarget =
  | "brief"
  | "fundamentals"
  | "frameworks"
  | "valuation"
  | "monitoring"
  | "advisor";

export interface DecisionMapRow {
  id: DecisionMapTarget;
  question: string;
  answer: string;
  /** Engine 2 not shipped — show planned, no fake strength signal. */
  planned?: boolean;
  /** Answer needs a selected ticker; portfolio fallback may still show. */
  needsTicker?: boolean;
}

const FRAMEWORK_SHORT: Record<FrameworkId, string> = {
  graham: "Graham",
  financial_strength: "FS",
};

/** Compact framework score line: "Graham 72 · FS 81" or "—". */
export function formatFrameworkAnswer(row: ThesisTicker | null): string {
  if (row == null || row.frameworks.length === 0) return "—";
  const parts = row.frameworks.map((card) => {
    const short =
      FRAMEWORK_SHORT[card.framework] ?? card.label.split(" ")[0] ?? card.framework;
    return `${short} ${formatFrameworkScore(card.score)}`;
  });
  return parts.join(" · ");
}

/** MoS stars + rating, or "—". */
export function formatValuationAnswer(row: ThesisTicker | null): string {
  if (row == null) return "—";
  const mos = row.margin_of_safety;
  if (mos == null) return "—";
  const stars = formatMosStars(mos.stars);
  const rating = mos.rating?.trim();
  if (stars === "—" && !rating) return "—";
  if (stars === "—") return rating;
  if (!rating) return stars;
  return `${stars} · ${rating}`;
}

/** Current thesis-change verdict, or "—". */
export function formatMonitoringAnswer(row: ThesisTicker | null): string {
  if (row == null) return "—";
  return formatThesisVerdict(row.monitoring?.current?.verdict);
}

/** Advisor conclusion · confidence, or "—". */
export function formatAdvisorAnswer(row: ThesisTicker | null): string {
  if (row == null) return "—";
  const insight = row.advisor;
  if (insight == null) return "—";
  const conclusion =
    insight.conclusion_label?.trim() ||
    formatAdvisorConclusion(insight.conclusion);
  const conf = formatAdvisorConfidence(insight.confidence);
  if (conf === "—") return conclusion;
  return `${conclusion} · ${conf}`;
}

/** Portfolio-level valuation rollup when no ticker is selected. */
export function formatPortfolioValuationAnswer(
  portfolio: PortfolioHealthRollup | null,
): string {
  if (portfolio == null) return "—";
  const und = portfolio.significantly_undervalued;
  const over = portfolio.overvalued;
  if (und === 0 && over === 0) return "No extreme valuation flags";
  return `${und} undervalued · ${over} overvalued`;
}

/** Portfolio-level thesis-change rollup when no ticker is selected. */
export function formatPortfolioMonitoringAnswer(
  portfolio: PortfolioHealthRollup | null,
): string {
  if (portfolio == null) return "—";
  const n = portfolio.thesis_broken;
  if (n === 0) return "No broken theses";
  return `${n} thesis broken`;
}

/**
 * Six decision questions (PRD §1.2) → one-line answers for the Decision Map.
 * Ticker-scoped when selected; portfolio fallbacks otherwise. Engine 2 stays planned.
 */
export function buildDecisionMapRows(
  selected: ThesisTicker | null,
  portfolio: PortfolioHealthRollup | null,
): DecisionMapRow[] {
  const hasTicker = selected != null;

  return [
    {
      id: "brief",
      question: "What changed that matters?",
      answer: "Open Brief",
    },
    {
      id: "fundamentals",
      question: "Is the company becoming stronger or weaker?",
      answer: "Planned",
      planned: true,
    },
    {
      id: "frameworks",
      question: "How does each philosophy score this?",
      answer: hasTicker
        ? formatFrameworkAnswer(selected)
        : "Select a ticker",
      needsTicker: !hasTicker,
    },
    {
      id: "valuation",
      question: "Am I paying too much?",
      answer: hasTicker
        ? formatValuationAnswer(selected)
        : formatPortfolioValuationAnswer(portfolio),
      needsTicker: !hasTicker && portfolio == null,
    },
    {
      id: "monitoring",
      question: "Has my thesis changed?",
      answer: hasTicker
        ? formatMonitoringAnswer(selected)
        : formatPortfolioMonitoringAnswer(portfolio),
      needsTicker: !hasTicker && portfolio == null,
    },
    {
      id: "advisor",
      question: "Buy more, hold, trim, or research further?",
      answer: hasTicker ? formatAdvisorAnswer(selected) : "Select a ticker",
      needsTicker: !hasTicker,
    },
  ];
}

/** DOM id for in-page section anchors (must match ThesisPage headings). */
export function decisionSectionId(target: DecisionMapTarget): string | null {
  if (target === "brief") return null;
  return `${target}-heading`;
}
