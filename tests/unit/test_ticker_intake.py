"""Flexible ticker intake — extract, dedupe, no list-move on duplicate."""

from __future__ import annotations

from pathlib import Path

from app.configs.settings import Settings
from app.schemas.watchlist import ListKind
from app.services import watchlist_store as store
from app.services.ticker_intake import (
    apply_intake,
    extract_tickers_from_text,
    extract_tickers_via_llm,
    filter_tickers_by_quote,
    looks_like_ocr_portfolio,
)

OCR_PORTFOLIO_SAMPLE = """My Portfolio A
41 Tickers

AMAT | on 507.67
Applied Materials,... 4 +5.90 (+1.18%)
SKHY \\ 143.73
SK hynix Inc. reel -5.27 (-3.54%)
SPCX 108.37
Space Exploration... Vor -3.83 (-3.41%)
HIVE 2.8300
HIVE Digital Tech... we -0.1700 (-5.67%)
APH | 160.70
Amphenol Corpor... |r, +0.88 (+0.55%)
COHR SR 262.89
Coherent Corp. . +13.83 (+5.55%)
CRDO nT 206.99
Credo Technology ... +5.91 (+2.94%)
LITE i 713.94
Lumentum Holdin... vem . +20.70 (+2.99%)
MRVL Wm 187.56
Marvell Technolog... r +4.26 (+2.32%)
AMD Lo 476.15
Advanced Micro D... sy -9.24 (1.90%)"""


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        watchlist_path=tmp_path / "watchlist.json",
        source_cache_dir=tmp_path / "sources",
        phase0_cache_dir=tmp_path / "phase0",
    )


def _ok_checker(ticker: str) -> str:
    return "ok"


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


def test_looks_like_ocr_portfolio() -> None:
    assert looks_like_ocr_portfolio(OCR_PORTFOLIO_SAMPLE)
    assert not looks_like_ocr_portfolio("nvda, aapl, MSFT")


def test_extract_ocr_portfolio_keeps_only_quote_row_tickers() -> None:
    out = extract_tickers_from_text(OCR_PORTFOLIO_SAMPLE, allow_llm=False)
    assert out.tickers == [
        "AMAT",
        "SKHY",
        "SPCX",
        "HIVE",
        "APH",
        "COHR",
        "CRDO",
        "LITE",
        "MRVL",
        "AMD",
    ]
    junk = {
        "ADVANCED",
        "APPLIED",
        "MATERIALS",
        "LO",
        "NT",
        "WM",
        "SR",
        "SPACE",
        "MICRO",
        "TECHNOLOGY",
        "DIGITAL",
        "LUMENTUM",
        "MARVELL",
        "AMPHENOL",
        "COHERENT",
        "CREDO",
        "HYNIX",
        "SK",
        "VOR",
        "VEM",
        "SY",
        "REEL",
    }
    assert junk.isdisjoint(out.tickers)


def test_extract_ocr_llm_fallback_when_regex_empty() -> None:
    # Prices present but no leading ALL-CAPS ticker+price rows.
    messy = (
        "My Portfolio\n"
        "Price 100.00 (+1.20%)\n"
        "Price 200.50 (-0.40%)\n"
        "Price 12.34 (+3.00%)\n"
    )

    def fake_llm(_prompt: str) -> str:
        return '["NVDA", "AAPL", "Advanced", "Materials"]'

    out = extract_tickers_from_text(messy, llm_caller=fake_llm, allow_llm=True)
    # Company-name debris blocked; format-valid symbols kept for quote check.
    assert out.tickers == ["NVDA", "AAPL"]


def test_parse_llm_rejects_non_json_gracefully() -> None:
    assert extract_tickers_via_llm(
        "AMAT AMD",
        llm_caller=lambda _p: "sorry, no tickers",
    ) == []


def test_filter_tickers_by_quote() -> None:
    def checker(ticker: str) -> str:
        if ticker in {"FAKE", "ZZZZ"}:
            return "not_found"
        if ticker == "FLAKY":
            return "unknown"
        return "ok"

    accepted, rejected = filter_tickers_by_quote(
        ["AAPL", "FAKE", "FLAKY", "MSFT"],
        quote_checker=checker,
    )
    assert accepted == ["AAPL", "FLAKY", "MSFT"]
    assert rejected == ["FAKE"]


def test_apply_skips_existing_no_move(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    store.put_membership(["NVDA"], ["AAPL"], s)
    result = apply_intake(
        "NVDA, MSFT, AAPL, !!!",
        ListKind.WATCHED,
        app_settings=s,
        quote_checker=_ok_checker,
    )
    assert result.added == ["MSFT"]
    assert result.skipped_duplicate == ["NVDA", "AAPL"]
    # NVDA stays Held — intake must not move to Watched
    m = store.get_membership(s)
    assert m.held == ["NVDA"]
    assert "MSFT" in m.watched
    assert "AAPL" in m.watched


def test_apply_rejects_quote_not_found(tmp_path: Path) -> None:
    s = _settings(tmp_path)

    def checker(ticker: str) -> str:
        return "ok" if ticker == "AAPL" else "not_found"

    result = apply_intake(
        "AAPL, FAKE, ZZZZ",
        ListKind.WATCHED,
        app_settings=s,
        quote_checker=checker,
    )
    assert result.added == ["AAPL"]
    assert set(result.rejected_invalid) >= {"FAKE", "ZZZZ"}


def test_apply_ocr_screenshot_sample(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    result = apply_intake(
        OCR_PORTFOLIO_SAMPLE,
        ListKind.WATCHED,
        app_settings=s,
        quote_checker=_ok_checker,
    )
    assert "AMD" in result.added
    assert "AMAT" in result.added
    assert "ADVANCED" not in result.added
    assert "LO" not in result.added
    assert "NT" not in result.added


def test_apply_csv_row_list_kind(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    text = "symbol,kind\nTSLA,held\nAMD,watched\n"
    result = apply_intake(
        text,
        ListKind.WATCHED,
        app_settings=s,
        quote_checker=_ok_checker,
    )
    assert set(result.added) == {"TSLA", "AMD"}
    m = store.get_membership(s)
    assert m.held == ["TSLA"]
    assert m.watched == ["AMD"]


def test_apply_empty_error(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    result = apply_intake(
        "hello world stock prices",
        ListKind.HELD,
        app_settings=s,
        quote_checker=_ok_checker,
    )
    assert result.added == []
    assert result.error_message
    assert "No tickers" in result.error_message or "No valid" in result.error_message
