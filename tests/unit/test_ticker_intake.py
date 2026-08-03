"""Flexible ticker intake — extract, dedupe, no list-move on duplicate."""

from __future__ import annotations

from pathlib import Path

from app.configs.settings import Settings
from app.schemas.watchlist import ListKind
from app.services import watchlist_store as store
from app.services.ticker_intake import apply_intake, extract_tickers_from_text


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        watchlist_path=tmp_path / "watchlist.json",
        source_cache_dir=tmp_path / "sources",
        phase0_cache_dir=tmp_path / "phase0",
    )


def test_extract_comma_and_whitespace_paste() -> None:
    out = extract_tickers_from_text("nvda, aapl  MSFT\nGOOG")
    assert out.tickers == ["NVDA", "AAPL", "MSFT", "GOOG"]


def test_extract_csv_with_header_and_list_kind() -> None:
    text = "ticker,list\nNVDA,held\nAAPL,watched\nnot-a-ticker,held\n"
    out = extract_tickers_from_text(text)
    assert out.tickers == ["NVDA", "AAPL"]
    assert out.list_kinds["NVDA"] == ListKind.HELD
    assert out.list_kinds["AAPL"] == ListKind.WATCHED
    assert "not-a-ticker" in " ".join(out.rejected_invalid).lower() or out.rejected_invalid


def test_extract_dedupes_within_upload() -> None:
    out = extract_tickers_from_text("NVDA nvda AAPL NVDA")
    assert out.tickers == ["NVDA", "AAPL"]


def test_extract_empty() -> None:
    out = extract_tickers_from_text("   the and for stock market   ")
    assert out.tickers == []


def test_extract_brk_b() -> None:
    out = extract_tickers_from_text("BRK.B meta")
    assert "BRK.B" in out.tickers
    assert "META" in out.tickers


def test_apply_skips_existing_no_move(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    store.put_membership(["NVDA"], ["AAPL"], s)
    result = apply_intake(
        "NVDA, MSFT, AAPL, !!!",
        ListKind.WATCHED,
        app_settings=s,
    )
    assert result.added == ["MSFT"]
    assert result.skipped_duplicate == ["NVDA", "AAPL"]
    # NVDA stays Held — intake must not move to Watched
    m = store.get_membership(s)
    assert m.held == ["NVDA"]
    assert "MSFT" in m.watched
    assert "AAPL" in m.watched


def test_apply_csv_row_list_kind(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    text = "symbol,kind\nTSLA,held\nAMD,watched\n"
    result = apply_intake(text, ListKind.WATCHED, app_settings=s)
    assert set(result.added) == {"TSLA", "AMD"}
    m = store.get_membership(s)
    assert m.held == ["TSLA"]
    assert m.watched == ["AMD"]


def test_apply_empty_error(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    result = apply_intake("hello world stock prices", ListKind.HELD, app_settings=s)
    assert result.added == []
    assert result.error_message
    assert "No tickers" in result.error_message or "No valid" in result.error_message
