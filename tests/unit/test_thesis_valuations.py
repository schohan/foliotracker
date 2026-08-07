"""Valuation Engine T2 — locked Graham / Buffett / Modern formulas."""

from __future__ import annotations

import pytest

from app.schemas.financials import FinancialMetrics, StatementSummary
from app.schemas.thesis import INSUFFICIENT_DATA, ValuationSchool
from app.services.thesis_valuations import (
    margin_of_safety_for,
    valuation_set_for,
)


def _method(vs, school: ValuationSchool, mid: str):
    bucket = {
        ValuationSchool.GRAHAM: vs.graham,
        ValuationSchool.BUFFETT: vs.buffett,
        ValuationSchool.MODERN: vs.modern,
    }[school]
    return next(m for m in bucket if m.id == mid)


def _rich(**overrides) -> FinancialMetrics:
    base = dict(
        ticker="NVDA",
        eps_trailing=5.0,
        trailing_pe=10.0,
        earnings_growth=0.10,
        total_cash=200.0,
        total_debt=80.0,
        market_cap=100.0,
        free_cash_flow=10.0,
        revenue_ttm=50.0,
        enterprise_value=120.0,
        ev_to_ebitda=15.0,
        peg_ratio=1.2,
        gross_margin=0.55,
        operating_margin=0.30,
        price_to_book=2.0,
        balance_sheet=StatementSummary(
            total_assets=400.0,
            total_liabilities=50.0,
            total_cash=200.0,
            total_debt=80.0,
        ),
    )
    base.update(overrides)
    return FinancialMetrics(**base)


def test_graham_intrinsic_and_mos_math() -> None:
    # V = 5 × (8.5 + 2·10) = 142.5; P = 50; MoS = 92.5/142.5 ≈ 0.649
    vs = valuation_set_for(_rich())
    intrinsic = _method(vs, ValuationSchool.GRAHAM, "intrinsic")
    assert intrinsic.value == pytest.approx(142.5)
    mos = _method(vs, ValuationSchool.GRAHAM, "margin_of_safety")
    assert mos.value == pytest.approx(0.6491, abs=1e-3)
    # Firm intrinsic = market × V / P = 100 × 142.5 / 50 = 285
    assert vs.ladder.intrinsic == pytest.approx(285.0)


def test_graham_growth_clamped_at_15_percent() -> None:
    a = valuation_set_for(_rich(earnings_growth=0.15))
    b = valuation_set_for(_rich(earnings_growth=0.80))
    assert _method(a, ValuationSchool.GRAHAM, "intrinsic").value == _method(
        b, ValuationSchool.GRAHAM, "intrinsic"
    ).value


def test_ncav_and_net_net() -> None:
    vs = valuation_set_for(_rich())
    ncav = _method(vs, ValuationSchool.GRAHAM, "ncav")
    assert ncav.value == pytest.approx(150.0)  # 200 − 50
    nn = _method(vs, ValuationSchool.GRAHAM, "net_net")
    assert nn.value == pytest.approx(1.5)
    assert "undervalued" in nn.detail


def test_liquidation_haircut() -> None:
    # cash + 0.5*(assets−cash) − liabilities = 200 + 0.5*200 − 50 = 250
    vs = valuation_set_for(_rich())
    liq = _method(vs, ValuationSchool.GRAHAM, "liquidation")
    assert liq.value == pytest.approx(250.0)
    assert vs.ladder.liquidation == pytest.approx(250.0)


def test_adjusted_book_prefers_balance_sheet() -> None:
    vs = valuation_set_for(_rich())
    adj = _method(vs, ValuationSchool.GRAHAM, "adjusted_book")
    assert adj.value == pytest.approx(350.0)  # 400 − 50


def test_adjusted_book_fallback_to_pb() -> None:
    vs = valuation_set_for(
        _rich(balance_sheet=None, market_cap=200.0, price_to_book=2.0)
    )
    adj = _method(vs, ValuationSchool.GRAHAM, "adjusted_book")
    assert adj.value == pytest.approx(100.0)
    assert "fallback" in adj.detail


def test_owner_earnings_is_fcf_proxy() -> None:
    vs = valuation_set_for(_rich())
    oe = _method(vs, ValuationSchool.BUFFETT, "owner_earnings")
    assert oe.value == pytest.approx(10.0)
    assert "FCF proxy" in oe.detail


def test_fcf_yield_and_capital_efficiency() -> None:
    vs = valuation_set_for(_rich())
    assert _method(vs, ValuationSchool.BUFFETT, "fcf_yield").value == pytest.approx(0.10)
    assert _method(vs, ValuationSchool.BUFFETT, "capital_efficiency").value == pytest.approx(
        0.20
    )


def test_roic_always_null() -> None:
    vs = valuation_set_for(_rich())
    roic = _method(vs, ValuationSchool.BUFFETT, "roic")
    assert roic.value is None
    assert INSUFFICIENT_DATA in roic.detail


def test_dcf_gordon_and_reverse() -> None:
    # g = clamp(0.10, 0, 0.04) = 0.04; DCF = 10×1.04/(0.10−0.04) = 173.333…
    vs = valuation_set_for(_rich())
    dcf = _method(vs, ValuationSchool.MODERN, "dcf")
    assert dcf.value == pytest.approx(173.333, abs=1e-2)
    # implied g = (100*0.10 − 10) / (100 + 10) = 0/110 = 0
    rdcf = _method(vs, ValuationSchool.MODERN, "reverse_dcf")
    assert rdcf.value == pytest.approx(0.0)


def test_ev_multiples_and_peg_passthrough() -> None:
    vs = valuation_set_for(_rich())
    assert _method(vs, ValuationSchool.MODERN, "ev_ebitda").value == pytest.approx(15.0)
    assert _method(vs, ValuationSchool.MODERN, "ev_fcf").value == pytest.approx(12.0)
    assert _method(vs, ValuationSchool.MODERN, "peg").value == pytest.approx(1.2)


def test_historical_bands_and_sector_always_null() -> None:
    vs = valuation_set_for(_rich())
    for mid in ("hist_pe_bands", "hist_ps_bands", "hist_pb_bands", "sector_relative"):
        m = _method(vs, ValuationSchool.MODERN, mid)
        assert m.value is None
        assert INSUFFICIENT_DATA in m.detail


def test_ladder_replacement_null_and_expected_fair_median() -> None:
    vs = valuation_set_for(_rich())
    assert vs.ladder.replacement is None
    assert vs.ladder.market == pytest.approx(100.0)
    assert vs.ladder.enterprise == pytest.approx(120.0)
    # intrinsic 285, dcf ≈173.33, adjusted book 350 → median 285
    assert vs.ladder.expected_fair == pytest.approx(285.0)


def test_margin_of_safety_view_stars() -> None:
    # MoS ≈ 64.9% → 5 stars, Excellent
    view = margin_of_safety_for(_rich())
    assert view.intrinsic_value == pytest.approx(142.5)
    assert view.market_price == pytest.approx(50.0)
    assert view.stars == 5
    assert view.rating.startswith("Excellent")


def test_margin_of_safety_poor_one_star() -> None:
    # g=0 → V=42.5; P=50 → MoS negative → Poor / 1 star
    view = margin_of_safety_for(_rich(earnings_growth=None, trailing_pe=10.0))
    assert view.stars == 1
    assert view.rating.startswith("Poor")


def test_missing_eps_nulls_intrinsic_and_mos() -> None:
    vs = valuation_set_for(_rich(eps_trailing=None))
    assert _method(vs, ValuationSchool.GRAHAM, "intrinsic").value is None
    assert INSUFFICIENT_DATA in _method(vs, ValuationSchool.GRAHAM, "intrinsic").detail
    view = margin_of_safety_for(_rich(eps_trailing=None))
    assert view.intrinsic_value is None
    assert view.stars is None


def test_dcf_null_when_fcf_non_positive() -> None:
    vs = valuation_set_for(_rich(free_cash_flow=0.0, cash_flow=None))
    assert _method(vs, ValuationSchool.MODERN, "dcf").value is None
