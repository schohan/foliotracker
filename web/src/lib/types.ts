export type Phase0Status = "ok" | "partial" | "error";
export type ListKind = "held" | "watched";
export type BulkAction = "remove" | "move_to_held" | "move_to_watched";
export type AppView = "watchlist" | "risk" | "brief" | "thesis";
export type BriefGenerationStatus = "complete" | "stale" | "partial";
export type BriefTickerStatus = "ok" | "partial" | "unavailable";
export type BriefInsightMode = "deterministic" | "canned" | "llm";
export type BriefPriority = "high" | "medium";
export type BriefSentiment = "positive" | "negative" | "neutral";
export type BriefMarketRisk = "low" | "medium" | "high";
export type BriefFilter =
  | "all"
  | "high"
  | "positive"
  | "negative"
  | "earnings"
  | "analyst"
  | "products"
  | "management"
  | "sec"
  | "macro"
  | "held"
  | "unread";

export interface BriefSource {
  label: string;
  url: string | null;
}

export interface BriefInsight {
  what_happened: string;
  why: string;
  market_reaction: string;
  should_long_term_care: string;
  confidence_label: string;
  suggested_action: string;
  explain_busy: string;
  provider: BriefInsightMode;
}

export interface BriefBullet {
  text: string;
  category: string;
  severity: number;
  evidence_ids: string[];
  source_url: string | null;
  status: "ok";
  event_key: string;
  impact_score: number;
  priority: BriefPriority;
  sentiment: BriefSentiment;
  headline: string;
  one_line_summary: string;
  why_it_matters: string[];
  portfolio_impact: string;
  suggested_action: string;
  confidence: number;
  sources: BriefSource[];
  insight: BriefInsight | null;
}

export interface QuietTicker {
  ticker: string;
  list_kind: ListKind;
}

export interface BriefSummary {
  holdings_count: number;
  high_count: number;
  medium_count: number;
  quiet_count: number;
  positive_count: number;
  negative_count: number;
  neutral_count: number;
  themes: string[];
  market_risk: BriefMarketRisk;
  biggest_story: string | null;
  biggest_risk: string | null;
  biggest_opportunity: string | null;
}

export interface BriefTicker {
  ticker: string;
  list_kind: ListKind;
  status: BriefTickerStatus;
  daily_return: number | null;
  move_score: number | null;
  event_severity: number | null;
  rank_score: number;
  impact_score: number;
  priority: BriefPriority | null;
  sentiment: BriefSentiment;
  headline: string | null;
  suggested_action: string | null;
  insight: BriefInsight | null;
  bullets: BriefBullet[];
  trailing_pe: number | null;
  return_1y: number | null;
  growth_score: number | null;
  value_score: number | null;
  risk_score: number | null;
}

export interface DailyBrief {
  generated_at: string;
  window_hours: number;
  generation_status: BriefGenerationStatus;
  universe_count: number;
  tickers_considered: number;
  tickers: BriefTicker[];
  quiet_tickers: QuietTicker[];
  summary: BriefSummary | null;
  insight_mode: BriefInsightMode;
  gaps: string[];
  empty_message: string | null;
  disclaimer: string;
}

export interface WatchlistMembership {
  held: string[];
  watched: string[];
}

export interface WatchlistTickerSummary {
  ticker: string;
  list_kind: ListKind;
  status: Phase0Status | null;
  growth_score: number | null;
  value_score: number | null;
  risk_score: number | null;
  profitability_score: number | null;
  moat_score: number | null;
  forward_pe: number | null;
  thesis_one_liner: string | null;
  conflict_count: number;
  cache_hit: boolean | null;
  request_id: string | null;
  error_message: string | null;
  updated_at: string | null;
}

export interface WatchlistState {
  membership: WatchlistMembership;
  summaries: WatchlistTickerSummary[];
  disclaimer: string;
}

export interface EvidenceConflict {
  id: string;
  topic: string;
  item_ids: string[];
  summary: string;
  severity: "info" | "warn";
}

export interface EvidenceItem {
  id: string;
  type: string;
  source: string;
  confidence: number;
  citation?: string | null;
  data?: Record<string, unknown>;
}

export interface Scorecard {
  ticker: string;
  growth_score: number | null;
  value_score: number | null;
  profitability_score: number | null;
  moat_score: number | null;
  risk_score: number | null;
  execution_score: number | null;
}

export interface ThesisClaim {
  text: string;
  evidence_ids: string[];
}

export interface InvestmentThesis {
  ticker: string;
  thesis: string;
  claims: ThesisClaim[];
  bull_case?: string | null;
  bear_case?: string | null;
  key_risks?: string[];
}

export interface Phase0Result {
  ticker: string;
  status: Phase0Status;
  evidence: {
    ticker: string;
    items: EvidenceItem[];
    conflicts: EvidenceConflict[];
    status: string;
  } | null;
  thesis: InvestmentThesis | null;
  scorecard: Scorecard | null;
  fundamentals: Record<string, unknown> | null;
  error_message: string | null;
  error_code: string | null;
  disclaimer: string;
  cache_hit: boolean;
  request_id: string;
}

export interface ResearchResponse {
  result: Phase0Result;
  list_kind: ListKind | null;
}

export interface HeldPositionRisk {
  ticker: string;
  weight: number;
  sector: string | null;
  risk_score: number | null;
  status: Phase0Status | null;
}

export interface SectorBucket {
  sector: string;
  weight: number;
  count: number;
  tickers: string[];
}

export interface PairCorrelation {
  ticker_a: string;
  ticker_b: string;
  correlation: number;
  overlap_days: number;
  window: string;
}

export interface PortfolioRiskSnapshot {
  status: Phase0Status;
  held_count: number;
  equal_weight: boolean;
  positions: HeldPositionRisk[];
  sector_buckets: SectorBucket[];
  top_correlations: PairCorrelation[];
  correlation_pairs_known: number;
  top_name_weight: number | null;
  avg_risk_score: number | null;
  risk_scores_known: number;
  gaps: string[];
  disclaimer: string;
}

export type FrameworkId = "graham" | "financial_strength";
export type CheckStatus = "pass" | "fail" | "unknown";
export type ThesisGenerationStatus = "complete" | "partial";
export type ValuationSchool = "graham" | "buffett" | "modern";
export type ValuationUnit = "currency" | "ratio" | "multiple" | "percent";
export type AssetVerdict =
  | "possible_undervaluation"
  | "fair"
  | "possible_overvaluation";
export type ThesisVerdict =
  | "no_change"
  | "strengthened"
  | "slightly_weaker"
  | "broken";
export type ThesisInsightMode = "deterministic" | "canned" | "llm";
export type AdvisorConclusion =
  | "buy_more"
  | "hold"
  | "trim"
  | "research_further"
  | "wait";

export interface FrameworkCheck {
  name: string;
  status: CheckStatus;
  value: number | null;
  rating: string;
  points: number | null;
  weight: number;
  inputs: string[];
  detail: string;
}

export interface FrameworkScorecard {
  framework: FrameworkId;
  label: string;
  score: number | null;
  checks: FrameworkCheck[];
  coverage: number;
}

export interface ValuationMethod {
  id: string;
  label: string;
  school: ValuationSchool;
  value: number | null;
  unit: ValuationUnit;
  inputs: string[];
  detail: string;
}

export interface ValuationLadder {
  market: number | null;
  intrinsic: number | null;
  liquidation: number | null;
  replacement: number | null;
  enterprise: number | null;
  expected_fair: number | null;
}

export interface ValuationSet {
  graham: ValuationMethod[];
  buffett: ValuationMethod[];
  modern: ValuationMethod[];
  ladder: ValuationLadder;
}

export interface MarginOfSafetyView {
  intrinsic_value: number | null;
  market_price: number | null;
  margin_of_safety: number | null;
  stars: number | null;
  rating: string;
  detail: string;
}

export interface AssetLine {
  name: string;
  value: number | null;
}

export interface AssetBreakdown {
  assets: AssetLine[];
  liabilities: AssetLine[];
  adjusted_net_assets: number | null;
  market_cap: number | null;
  difference_pct: number | null;
  verdict: AssetVerdict | null;
  detail: string;
}

export interface ThesisChange {
  verdict: ThesisVerdict;
  as_of: string;
  evidence: string[];
  narrative: string;
  insight_mode: string;
}

export interface ThesisMonitoring {
  original_thesis: string;
  current: ThesisChange | null;
  timeline: ThesisChange[];
}

export interface AdvisorInsight {
  reasoning: string[];
  conclusion: AdvisorConclusion;
  conclusion_label: string;
  confidence: number;
  provider: string;
}

export interface ThesisExplainAnswer {
  ticker: string;
  question_id: string;
  question: string;
  answer: string;
  evidence: string[];
  provider: string;
}

export interface ThesisTicker {
  ticker: string;
  list_kind: ListKind;
  name: string | null;
  sector: string | null;
  frameworks: FrameworkScorecard[];
  valuation: ValuationSet | null;
  margin_of_safety: MarginOfSafetyView | null;
  assets: AssetBreakdown | null;
  monitoring: ThesisMonitoring | null;
  advisor: AdvisorInsight | null;
  sources_used: string[];
  gaps: string[];
}

export interface ThesisDashboard {
  generated_at: string;
  generation_status: ThesisGenerationStatus;
  universe_count: number;
  tickers_considered: number;
  tickers: ThesisTicker[];
  frameworks: FrameworkId[];
  gaps: string[];
  empty_message: string | null;
  disclaimer: string;
}

export interface WatchlistIntakeResponse {
  added: string[];
  skipped_duplicate: string[];
  rejected_invalid: string[];
  added_count: number;
  skipped_duplicate_count: number;
  rejected_invalid_count: number;
  state: WatchlistState;
  error_message: string | null;
  disclaimer: string;
}

export interface WatchlistBulkResponse {
  affected: string[];
  skipped_not_found: string[];
  skipped_noop: string[];
  affected_count: number;
  skipped_not_found_count: number;
  skipped_noop_count: number;
  state: WatchlistState;
  disclaimer: string;
}
