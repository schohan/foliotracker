export type Phase0Status = "ok" | "partial" | "error";
export type ListKind = "held" | "watched";

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
