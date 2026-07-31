import type {
  ListKind,
  PortfolioRiskSnapshot,
  ResearchResponse,
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

export function removeTicker(ticker: string): Promise<WatchlistState> {
  return request(`/api/watchlist/tickers/${encodeURIComponent(ticker)}`, {
    method: "DELETE",
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
