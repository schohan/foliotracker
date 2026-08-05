"""Brief generator — gate, rank, cap, dedupe, empty states."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from app.configs.settings import Settings
from app.schemas.brief import BriefEventCategory, BriefGenerationStatus, BriefTickerStatus
from app.schemas.evidence import Evidence
from app.schemas.financials import FinancialMetrics, PriceReturns
from app.schemas.watchlist import ListKind
from app.services import watchlist_store as wstore
from app.services.brief_classify import ClassifiedEvent
from app.services.brief_service import (
    EMPTY_MATERIAL_MSG,
    EMPTY_UNIVERSE_MSG,
    TickerWorkResult,
    build_ticker_row,
    generate_daily_brief,
)

def _settings(tmp_path: Path) -> Settings:
    return Settings(
        watchlist_path=tmp_path / "w.json",
        source_cache_dir=tmp_path / "sources",
        phase0_cache_dir=tmp_path / "phase0",
        brief_store_path=tmp_path / "briefs.json",
        brief_miss_log_path=tmp_path / "misses.jsonl",
        brief_max_tickers=15,
        brief_max_bullets_per_ticker=5,
        brief_generate_budget_seconds=60,
        brief_max_workers=4,
    )


def _event(
    title: str,
    severity: int = 3,
    category: BriefEventCategory = BriefEventCategory.ANALYST_RATING,
) -> ClassifiedEvent:
    ev = Evidence(
        id=f"ev_{title[:8]}",
        type="news",
        source="Google News",
        confidence=0.7,
        citation="https://example.com/x",
        data={"title": title, "url": "https://example.com/x"},
    )
    return ClassifiedEvent(
        category=category,
        severity=severity,
        evidence=ev,
        title=title,
        source_url="https://example.com/x",
        published_at=datetime(2024, 6, 1, tzinfo=timezone.utc),
    )


def _work(
    ticker: str,
    *,
    kind: ListKind = ListKind.WATCHED,
    daily_return: float | None = None,
    events: list[ClassifiedEvent] | None = None,
    sources_partial: bool = False,
    metrics: FinancialMetrics | None = None,
) -> TickerWorkResult:
    return TickerWorkResult(
        ticker=ticker,
        list_kind=kind,
        daily_return=daily_return,
        events=events or [],
        bundle_ids={e.evidence.id for e in (events or [])},
        metrics=metrics,
        phase0=None,
        gaps=[],
        sources_partial=sources_partial,
    )


def test_empty_universe(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    brief = generate_daily_brief(app_settings=s)
    assert brief.universe_count == 0
    assert brief.empty_message == EMPTY_UNIVERSE_MSG
    assert brief.generation_status == BriefGenerationStatus.COMPLETE


def test_held_wins_dedupe_and_gate_rank_cap(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    # NVDA in both — Held wins
    wstore.put_membership(["NVDA", "AAPL"], ["NVDA", "MSFT", "GOOG"], s)

    works = {
        "NVDA": _work(
            "NVDA",
            kind=ListKind.HELD,
            daily_return=0.06,
            events=[_event("NVDA upgrade", 3)],
        ),
        "AAPL": _work("AAPL", kind=ListKind.HELD, daily_return=0.01),
        "MSFT": _work(
            "MSFT",
            kind=ListKind.WATCHED,
            daily_return=None,
            events=[
                _event(
                    "MSFT guidance",
                    5,
                    BriefEventCategory.EARNINGS_GUIDANCE,
                )
            ],
        ),
        "GOOG": _work("GOOG", kind=ListKind.WATCHED, daily_return=0.02),
    }

    def worker(ticker: str, kind: ListKind) -> TickerWorkResult:
        w = works[ticker]
        assert w.list_kind == kind or ticker == "NVDA"
        return works[ticker]

    brief = generate_daily_brief(app_settings=s, worker_fn=worker)
    tickers = [t.ticker for t in brief.tickers]
    assert "AAPL" not in tickers  # quiet
    assert "GOOG" not in tickers
    assert "NVDA" in tickers
    assert "MSFT" in tickers
    quiet = {q.ticker for q in brief.quiet_tickers}
    assert "AAPL" in quiet
    assert "GOOG" in quiet
    nvda = next(t for t in brief.tickers if t.ticker == "NVDA")
    assert nvda.list_kind == "held"
    assert nvda.impact_score >= 80 or nvda.rank_score >= 3.0
    assert nvda.priority is not None
    assert nvda.bullets[0].insight is not None
    msft = next(t for t in brief.tickers if t.ticker == "MSFT")
    assert msft.impact_score >= 90
    assert brief.tickers[0].ticker == "MSFT"
    assert brief.summary is not None
    assert brief.summary.quiet_count >= 2
    assert brief.insight_mode.value == "deterministic"


def test_cap_15(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    # Letter-only symbols (ticker pattern rejects digits).
    held = [f"T{chr(65 + i)}" for i in range(20)]  # TA..TT
    wstore.put_membership(held, [], s)

    def worker(ticker: str, kind: ListKind) -> TickerWorkResult:
        idx = ord(ticker[1]) - 65
        return _work(
            ticker,
            kind=kind,
            daily_return=0.05 + idx * 0.001,
        )

    brief = generate_daily_brief(app_settings=s, worker_fn=worker)
    assert len(brief.tickers) == 15
    assert brief.summary is not None


def test_nothing_material_message(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    wstore.put_membership([], ["AAPL"], s)

    def worker(ticker: str, kind: ListKind) -> TickerWorkResult:
        return _work(ticker, kind=kind, daily_return=0.01)

    brief = generate_daily_brief(app_settings=s, worker_fn=worker)
    assert brief.tickers == []
    assert brief.empty_message == EMPTY_MATERIAL_MSG
    assert any(q.ticker == "AAPL" for q in brief.quiet_tickers)


def test_build_ticker_row_partial_and_move_only() -> None:
    row = build_ticker_row(
        _work(
            "XYZ",
            daily_return=0.09,
            sources_partial=True,
            metrics=FinancialMetrics(
                ticker="XYZ",
                trailing_pe=12.0,
                returns=PriceReturns(return_1y=0.2),
            ),
        ),
        max_bullets=5,
    )
    assert row is not None
    assert row.status == BriefTickerStatus.PARTIAL
    assert len(row.bullets) == 1
    assert row.bullets[0].category == BriefEventCategory.PRICE_MOVE
    assert row.move_score == 3
    assert row.trailing_pe == 12.0
    assert row.impact_score >= 50


def test_news_event_bypasses_move_gate() -> None:
    row = build_ticker_row(
        _work("ABC", daily_return=0.01, events=[_event("Product launch", 3)]),
        max_bullets=5,
    )
    assert row is not None
    assert len(row.bullets) == 1
    assert row.bullets[0].source_url
    assert row.bullets[0].why_it_matters
    assert row.suggested_action