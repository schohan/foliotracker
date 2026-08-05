import type {
  BriefInsight,
  BulkAction,
  DailyBrief,
  ListKind,
  PortfolioRiskSnapshot,
  ResearchResponse,
  WatchlistBulkResponse,
  WatchlistIntakeResponse,
  WatchlistState,
  WatchlistTickerSummary,
} from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    ...init,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch {
      /* keep statusText */
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return res.json() as Promise<T>;
}

export function fetchWatchlist(): Promise<WatchlistState> {
  return request("/api/watchlist");
}

export function addTicker(ticker: string, list_kind: ListKind): Promise<WatchlistState> {
  return request("/api/watchlist/tickers", {
    method: "POST",
    body: JSON.stringify({ ticker, list_kind }),
  });
}

export function intakeTickers(
  text: string,
  list_kind: ListKind,
): Promise<WatchlistIntakeResponse> {
  return request("/api/watchlist/intake", {
    method: "POST",
    body: JSON.stringify({ text, list_kind }),
  });
}

export function removeTicker(ticker: string): Promise<WatchlistState> {
  return request(`/api/watchlist/tickers/${encodeURIComponent(ticker)}`, {
    method: "DELETE",
  });
}

export function bulkWatchlistTickers(
  tickers: string[],
  action: BulkAction,
): Promise<WatchlistBulkResponse> {
  return request("/api/watchlist/bulk", {
    method: "POST",
    body: JSON.stringify({ tickers, action }),
  });
}

export function refreshTicker(ticker: string): Promise<WatchlistTickerSummary> {
  return request(`/api/watchlist/${encodeURIComponent(ticker)}/refresh`, {
    method: "POST",
  });
}

export function refreshAll(): Promise<{ summaries: WatchlistTickerSummary[] }> {
  return request("/api/watchlist/refresh", {
    method: "POST",
    body: JSON.stringify({ max_tickers: 8 }),
  });
}

export function fetchResearch(ticker: string): Promise<ResearchResponse> {
  return request(`/api/research/${encodeURIComponent(ticker)}`);
}

export function fetchRisk(): Promise<PortfolioRiskSnapshot> {
  return request("/api/risk");
}

export function fetchBrief(): Promise<DailyBrief | null> {
  return request("/api/brief");
}

export function fetchBriefHistory(limit = 14): Promise<DailyBrief[]> {
  return request(`/api/brief/history?limit=${limit}`);
}

export function generateBrief(force_refresh = false): Promise<DailyBrief> {
  return request("/api/brief/generate", {
    method: "POST",
    body: JSON.stringify({ force_refresh }),
  });
}

export function logBriefMiss(note: string): Promise<{ ts: string; note: string }> {
  return request("/api/brief/miss", {
    method: "POST",
    body: JSON.stringify({ note }),
  });
}

export function explainBriefEvent(body: {
  ticker: string;
  event_key?: string;
  category?: string;
  text?: string;
  daily_return?: number | null;
  list_kind?: ListKind;
}): Promise<BriefInsight> {
  return request("/api/brief/explain", {
    method: "POST",
    body: JSON.stringify(body),
  });
}
