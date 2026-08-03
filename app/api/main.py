"""FastAPI app — watchlist dashboard over Phase0Result."""

from __future__ import annotations

from typing import Callable

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.configs.settings import Settings, settings as default_settings
from app.schemas.brief import (
    BriefGenerateRequest,
    BriefMissLogRequest,
    DailyBrief,
)
from app.schemas.phase0 import Phase0Result
from app.schemas.ticker import InvalidTickerError, normalize_ticker
from app.schemas.portfolio import PortfolioRiskSnapshot
from app.schemas.watchlist import (
    BatchRefreshRequest,
    BatchRefreshResponse,
    ResearchResponse,
    WatchlistAddRequest,
    WatchlistIntakeRequest,
    WatchlistIntakeResponse,
    WatchlistPutRequest,
    WatchlistState,
    WatchlistTickerSummary,
)
from app.services import brief_store, watchlist_store as store
from app.services.brief_service import generate_daily_brief, get_latest_brief
from app.services.phase0_pipeline import run_phase0_research
from app.services.portfolio_risk_service import build_portfolio_risk
from app.services.ticker_intake import apply_intake
from app.services.watchlist_service import (
    get_watchlist_state,
    refresh_batch,
    refresh_ticker,
)


def create_app(
    *,
    app_settings: Settings | None = None,
    research_fn: Callable[..., Phase0Result] | None = None,
    brief_generate_fn: Callable[..., DailyBrief] | None = None,
) -> FastAPI:
    """Build the API app (injectable settings + research for tests)."""
    s = app_settings if app_settings is not None else default_settings
    fn = research_fn or run_phase0_research
    brief_fn = brief_generate_fn or generate_daily_brief

    app = FastAPI(title="FolioTracker", version="0.1.0")
    origins = [o.strip() for o in s.watchlist_cors_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/watchlist", response_model=WatchlistState)
    def get_watchlist() -> WatchlistState:
        return get_watchlist_state(s)

    @app.get("/api/risk", response_model=PortfolioRiskSnapshot)
    def get_risk() -> PortfolioRiskSnapshot:
        """Held-only equal-weight concentration (no research re-run)."""
        return build_portfolio_risk(app_settings=s)

    @app.get("/api/brief", response_model=DailyBrief | None)
    def get_brief() -> DailyBrief | None:
        """Latest persisted DailyBrief (null when none generated yet)."""
        return get_latest_brief(app_settings=s)

    @app.post("/api/brief/generate", response_model=DailyBrief)
    def post_brief_generate(
        body: BriefGenerateRequest | None = None,
    ) -> DailyBrief:
        """Sync Generate today (cache-first; ~60s wall budget)."""
        req = body or BriefGenerateRequest()
        return brief_fn(app_settings=s, force_refresh=req.force_refresh)

    @app.post("/api/brief/miss")
    def post_brief_miss(body: BriefMissLogRequest) -> dict[str, str]:
        """Append dogfood material-miss note."""
        return brief_store.append_miss_note(body.note, app_settings=s)

    @app.put("/api/watchlist", response_model=WatchlistState)
    def put_watchlist(body: WatchlistPutRequest) -> WatchlistState:
        store.put_membership(body.held, body.watched, s)
        return get_watchlist_state(s)

    @app.post("/api/watchlist/tickers", response_model=WatchlistState)
    def add_watchlist_ticker(body: WatchlistAddRequest) -> WatchlistState:
        try:
            store.add_ticker(body.ticker, body.list_kind, s)
        except InvalidTickerError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return get_watchlist_state(s)

    @app.post("/api/watchlist/intake", response_model=WatchlistIntakeResponse)
    def intake_watchlist_tickers(body: WatchlistIntakeRequest) -> WatchlistIntakeResponse:
        """Bulk add from paste/CSV/OCR/speech text. Skips existing; no research."""
        result = apply_intake(body.text, body.list_kind, app_settings=s)
        state = get_watchlist_state(s)
        if result.error_message and not result.added and not result.skipped_duplicate:
            raise HTTPException(status_code=400, detail=result.error_message)
        return WatchlistIntakeResponse(
            added=result.added,
            skipped_duplicate=result.skipped_duplicate,
            rejected_invalid=result.rejected_invalid,
            added_count=len(result.added),
            skipped_duplicate_count=len(result.skipped_duplicate),
            rejected_invalid_count=len(result.rejected_invalid),
            state=state,
            error_message=result.error_message,
        )

    @app.delete("/api/watchlist/tickers/{ticker}", response_model=WatchlistState)
    def delete_watchlist_ticker(ticker: str) -> WatchlistState:
        try:
            store.remove_ticker(ticker, s)
        except InvalidTickerError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return get_watchlist_state(s)

    # Batch path must be registered before /{ticker}/refresh.
    @app.post("/api/watchlist/refresh", response_model=BatchRefreshResponse)
    def refresh_many(body: BatchRefreshRequest | None = None) -> BatchRefreshResponse:
        req = body or BatchRefreshRequest()
        return refresh_batch(
            tickers=req.tickers,
            max_tickers=req.max_tickers,
            app_settings=s,
            research_fn=fn,
            skip_cache=False,
        )

    @app.post(
        "/api/watchlist/{ticker}/refresh",
        response_model=WatchlistTickerSummary,
    )
    def refresh_one(
        ticker: str,
        skip_cache: bool = Query(default=False),
    ) -> WatchlistTickerSummary:
        try:
            return refresh_ticker(
                ticker,
                app_settings=s,
                research_fn=fn,
                skip_cache=skip_cache,
            )
        except InvalidTickerError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/research/{ticker}", response_model=ResearchResponse)
    def get_research(
        ticker: str,
        skip_cache: bool = Query(default=False),
    ) -> ResearchResponse:
        try:
            normalized = normalize_ticker(ticker)
        except InvalidTickerError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        kind = store.list_kind_for(normalized, app_settings=s)
        result = fn(normalized, skip_cache=skip_cache)
        if kind is not None:
            from app.schemas.watchlist import summary_from_phase0
            from app.services.watchlist_store import now_utc, upsert_summary

            upsert_summary(
                summary_from_phase0(result, list_kind=kind, updated_at=now_utc()),
                s,
            )
        return ResearchResponse(result=result, list_kind=kind)

    return app


app = create_app()
