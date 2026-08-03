export type Phase0Status = "ok" | "partial" | "error";
export type ListKind = "held" | "watched";
export type BulkAction = "remove" | "move_to_held" | "move_to_watched";
export type AppView = "watchlist" | "risk" | "brief";
export type BriefGenerationStatus = "complete" | "stale" | "partial";
export type BriefTickerStatus = "ok" | "partial" | "unavailable";

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

export interface BriefBullet {
  text: string;
  category: string;
  severity: number;
  evidence_ids: string[];
  source_url: string | null;
  status: "ok";
}

export interface BriefTicker {
  ticker: string;
  list_kind: ListKind;
  status: BriefTickerStatus;
  daily_return: number | null;
  move_score: number | null;
  event_severity: number | null;
  rank_score: number;
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
