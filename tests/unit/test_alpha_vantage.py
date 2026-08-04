"""Alpha Vantage OVERVIEW parse tests."""

from __future__ import annotations

import pytest

from app.tools.finance.alpha_vantage import (
    ToolParseError,
    ToolUpstreamError,
    parse_overview_json,
)


def _overview(**overrides: object) -> dict:
    base = {
        "Symbol": "IBM",
        "Name": "International Business Machines",
        "Sector": "TECHNOLOGY",
        "Industry": "INFORMATION TECHNOLOGY SERVICES",
        "Description": "A technology company.",
        "MarketCapitalization": "201795764000",
        "PERatio": "18.35",
        "EPS": "11.67",
        "TrailingPE": "18.35",
        "ForwardPE": "16.98",
        "PEGRatio": "1.45",
        "PriceToSalesRatioTTM": "2.9",
        "PriceToBookRatio": "6.1",
        "EVToRevenue": "3.2",
        "EVToEBITDA": "12.4",
        "ProfitMargin": "0.121",
        "OperatingMarginTTM": "0.157",
        "ReturnOnAssetsTTM": "0.062",
        "ReturnOnEquityTTM": "0.345",
        "RevenueTTM": "69094998000",
        "GrossProfitTTM": "40144998000",
        "QuarterlyRevenueGrowthYOY": "0.011",
        "QuarterlyEarningsGrowthYOY": "-0.018",
    }
    base.update(overrides)
    return base


def test_parse_overview_maps_forward_pe() -> None:
    m = parse_overview_json(_overview(), ticker="IBM")
    assert m.ticker == "IBM"
    assert m.source_id == "alpha_vantage"
    assert m.forward_pe == 16.98
    assert m.pe_ratio == 18.35
    assert m.trailing_pe == 18.35
    assert m.eps_trailing == 11.67
    assert m.eps_forward is None  # not on OVERVIEW
    assert m.market_cap == 201795764000.0
    assert m.gross_margin == pytest.approx(40144998000 / 69094998000)
    assert m.peg_ratio == 1.45
    assert m.price_to_sales == 2.9
    assert m.price_to_book == 6.1
    assert m.ev_to_revenue == 3.2
    assert m.ev_to_ebitda == 12.4
    assert m.profit_margin == 0.121
    assert m.return_on_assets == 0.062
    assert m.revenue_ttm == 69094998000.0
    assert m.profile is not None
    assert m.profile.name == "International Business Machines"
    assert m.profile.sector == "TECHNOLOGY"


def test_parse_overview_rejects_rate_limit_note() -> None:
    with pytest.raises(ToolUpstreamError, match="Note"):
        parse_overview_json(
            {"Note": "Thank you for using Alpha Vantage! Our standard API call frequency is 25 requests per day."},
            ticker="IBM",
        )


def test_parse_overview_rejects_empty() -> None:
    with pytest.raises(ToolParseError, match="empty OVERVIEW"):
        parse_overview_json({}, ticker="IBM")


def test_parse_overview_rejects_non_numeric_market_only() -> None:
    with pytest.raises(ToolParseError, match="no usable OVERVIEW"):
        parse_overview_json(
            {"Symbol": "IBM", "Name": "IBM", "ForwardPE": "-", "PERatio": "N/A"},
            ticker="IBM",
        )


def test_parse_overview_forward_pe_only() -> None:
    m = parse_overview_json(
        {"Symbol": "AAPL", "ForwardPE": "22.5"},
        ticker="AAPL",
    )
    assert m.forward_pe == 22.5
    assert m.pe_ratio is None
