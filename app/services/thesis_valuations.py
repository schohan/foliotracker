"""Valuation Engine T2 — Graham / Buffett / Modern sets + six-value ladder + MoS.

Implements the locked spec tables in architecture.md "Valuation / net-asset
formula specs" (2026-08-07). Pure Python over the merged FundamentalsSnapshot;
missing inputs → method ``null`` ("insufficient data"), never invented.
"""

from __future__ import annotations

from statistics import median

from app.schemas.financials import FinancialMetrics
from app.schemas.thesis import (
    INSUFFICIENT_DATA,
    MarginOfSafetyView,
    ValuationLadder,
    ValuationMethod,
    ValuationSchool,
    ValuationSet,
    ValuationUnit,
)

# Graham locked constants (shared with thesis_frameworks MoS)
_GRAHAM_GROWTH_CAP = 0.15

# Modern DCF locked constants
_DCF_DISCOUNT_RATE = 0.10
_DCF_GROWTH_CAP = 0.04

# Liquidation: haircut on non-cash assets
_LIQUIDATION_NON_CASH_HAIRCUT = 0.5


def _null_method(
    *,
    id: str,
    label: str,
    school: ValuationSchool,
    unit: ValuationUnit,
    inputs: list[str],
    missing: list[str],
) -> ValuationMethod:
    return ValuationMethod(
        id=id,
        label=label,
        school=school,
        value=None,
        unit=unit,
        inputs=inputs,
        detail=f"{INSUFFICIENT_DATA}: {', '.join(missing)}",
    )


def _pe(m: FinancialMetrics) -> float | None:
    for candidate in (m.trailing_pe, m.pe_ratio):
        if candidate is not None and candidate > 0:
            return candidate
    return None


def _bs_liabilities(m: FinancialMetrics) -> float | None:
    if m.balance_sheet is None:
        return None
    return m.balance_sheet.total_liabilities


def _bs_assets(m: FinancialMetrics) -> float | None:
    if m.balance_sheet is None:
        return None
    return m.balance_sheet.total_assets


def _fcf(m: FinancialMetrics) -> float | None:
    if m.free_cash_flow is not None:
        return m.free_cash_flow
    if m.cash_flow is not None and m.cash_flow.free_cash_flow is not None:
        return m.cash_flow.free_cash_flow
    return None


def graham_intrinsic_per_share(m: FinancialMetrics) -> tuple[float | None, float | None, float]:
    """Return (V, P, g) or (None, None, g) when inputs insufficient."""
    eps = m.eps_trailing
    pe = _pe(m)
    growth = m.earnings_growth if m.earnings_growth is not None else 0.0
    g = max(0.0, min(_GRAHAM_GROWTH_CAP, growth))
    if eps is None or eps <= 0 or pe is None:
        return None, None, g
    v = eps * (8.5 + 2.0 * g * 100.0)
    p = pe * eps
    return v, p, g


def _ncav(m: FinancialMetrics) -> float | None:
    liabilities = _bs_liabilities(m)
    if m.total_cash is None or liabilities is None:
        return None
    return m.total_cash - liabilities


def _graham_methods(m: FinancialMetrics) -> tuple[list[ValuationMethod], float | None, float | None, float | None]:
    """Graham set + (firm_intrinsic, liquidation, adjusted_book) for ladder."""
    methods: list[ValuationMethod] = []

    # NCAV
    ncav = _ncav(m)
    ncav_inputs = ["total_cash", "balance_sheet.total_liabilities"]
    if ncav is None:
        methods.append(
            _null_method(
                id="ncav",
                label="NCAV (cash proxy)",
                school=ValuationSchool.GRAHAM,
                unit=ValuationUnit.CURRENCY,
                inputs=ncav_inputs,
                missing=["total_cash", "balance_sheet.total_liabilities"],
            )
        )
    else:
        methods.append(
            ValuationMethod(
                id="ncav",
                label="NCAV (cash proxy)",
                school=ValuationSchool.GRAHAM,
                value=ncav,
                unit=ValuationUnit.CURRENCY,
                inputs=ncav_inputs,
                detail="cash − liabilities (no current-assets breakdown)",
            )
        )

    # Net-Net ratio
    nn_inputs = ["total_cash", "balance_sheet.total_liabilities", "market_cap"]
    if ncav is None or m.market_cap is None or m.market_cap <= 0:
        missing = []
        if ncav is None:
            missing.extend(["total_cash", "balance_sheet.total_liabilities"])
        if m.market_cap is None or m.market_cap <= 0:
            missing.append("positive market_cap")
        methods.append(
            _null_method(
                id="net_net",
                label="Net-Net",
                school=ValuationSchool.GRAHAM,
                unit=ValuationUnit.RATIO,
                inputs=nn_inputs,
                missing=missing,
            )
        )
    else:
        ratio = ncav / m.market_cap
        methods.append(
            ValuationMethod(
                id="net_net",
                label="Net-Net",
                school=ValuationSchool.GRAHAM,
                value=ratio,
                unit=ValuationUnit.RATIO,
                inputs=nn_inputs,
                detail=(
                    "undervalued (NCAV ≥ market)"
                    if ratio >= 1.0
                    else "not net-net undervalued"
                ),
            )
        )

    # Intrinsic per-share + firm
    v, p, g = graham_intrinsic_per_share(m)
    intr_inputs = ["eps_trailing", "trailing_pe", "pe_ratio", "earnings_growth", "market_cap"]
    firm_intrinsic: float | None = None
    if v is None or p is None:
        missing = []
        if m.eps_trailing is None or m.eps_trailing <= 0:
            missing.append("eps_trailing")
        if _pe(m) is None:
            missing.append("positive trailing P/E")
        methods.append(
            _null_method(
                id="intrinsic",
                label="Intrinsic Value",
                school=ValuationSchool.GRAHAM,
                unit=ValuationUnit.CURRENCY,
                inputs=intr_inputs,
                missing=missing or ["eps_trailing / P/E"],
            )
        )
    else:
        methods.append(
            ValuationMethod(
                id="intrinsic",
                label="Intrinsic Value",
                school=ValuationSchool.GRAHAM,
                value=v,
                unit=ValuationUnit.CURRENCY,
                inputs=intr_inputs,
                detail=f"per-share Graham V (g={g:.0%})",
            )
        )
        if m.market_cap is not None and p > 0:
            firm_intrinsic = m.market_cap * v / p

    # Liquidation
    assets = _bs_assets(m)
    liabilities = _bs_liabilities(m)
    liq_inputs = ["total_cash", "balance_sheet.total_assets", "balance_sheet.total_liabilities"]
    liquidation: float | None = None
    if assets is None or liabilities is None:
        missing = []
        if assets is None:
            missing.append("balance_sheet.total_assets")
        if liabilities is None:
            missing.append("balance_sheet.total_liabilities")
        methods.append(
            _null_method(
                id="liquidation",
                label="Liquidation Value",
                school=ValuationSchool.GRAHAM,
                unit=ValuationUnit.CURRENCY,
                inputs=liq_inputs,
                missing=missing,
            )
        )
    else:
        cash = m.total_cash if m.total_cash is not None else 0.0
        liquidation = cash + _LIQUIDATION_NON_CASH_HAIRCUT * (assets - cash) - liabilities
        methods.append(
            ValuationMethod(
                id="liquidation",
                label="Liquidation Value",
                school=ValuationSchool.GRAHAM,
                value=liquidation,
                unit=ValuationUnit.CURRENCY,
                inputs=liq_inputs,
                detail="cash + 50% haircut on non-cash assets − liabilities",
            )
        )

    # Adjusted book
    adj_inputs = [
        "balance_sheet.total_assets",
        "balance_sheet.total_liabilities",
        "market_cap",
        "price_to_book",
    ]
    adjusted_book: float | None = None
    if assets is not None and liabilities is not None:
        adjusted_book = assets - liabilities
        methods.append(
            ValuationMethod(
                id="adjusted_book",
                label="Adjusted Book Value",
                school=ValuationSchool.GRAHAM,
                value=adjusted_book,
                unit=ValuationUnit.CURRENCY,
                inputs=adj_inputs,
                detail="assets − liabilities",
            )
        )
    elif (
        m.market_cap is not None
        and m.price_to_book is not None
        and m.price_to_book > 0
    ):
        adjusted_book = m.market_cap / m.price_to_book
        methods.append(
            ValuationMethod(
                id="adjusted_book",
                label="Adjusted Book Value",
                school=ValuationSchool.GRAHAM,
                value=adjusted_book,
                unit=ValuationUnit.CURRENCY,
                inputs=adj_inputs,
                detail="market_cap / price_to_book (BS fallback)",
            )
        )
    else:
        methods.append(
            _null_method(
                id="adjusted_book",
                label="Adjusted Book Value",
                school=ValuationSchool.GRAHAM,
                unit=ValuationUnit.CURRENCY,
                inputs=adj_inputs,
                missing=["balance_sheet assets/liabilities or market_cap/P/B"],
            )
        )

    # Margin of Safety (fraction) as a method for the set table
    mos_inputs = ["eps_trailing", "trailing_pe", "pe_ratio", "earnings_growth"]
    if v is None or p is None:
        methods.append(
            _null_method(
                id="margin_of_safety",
                label="Margin of Safety",
                school=ValuationSchool.GRAHAM,
                unit=ValuationUnit.PERCENT,
                inputs=mos_inputs,
                missing=["eps_trailing / P/E"],
            )
        )
    else:
        mos = (v - p) / v
        methods.append(
            ValuationMethod(
                id="margin_of_safety",
                label="Margin of Safety",
                school=ValuationSchool.GRAHAM,
                value=mos,
                unit=ValuationUnit.PERCENT,
                inputs=mos_inputs,
                detail=f"intrinsic {v:.2f} vs implied price {p:.2f}",
            )
        )

    return methods, firm_intrinsic, liquidation, adjusted_book


def _buffett_methods(m: FinancialMetrics) -> list[ValuationMethod]:
    methods: list[ValuationMethod] = []
    fcf = _fcf(m)

    # Owner earnings (FCF proxy)
    oe_inputs = ["free_cash_flow"]
    if fcf is None:
        methods.append(
            _null_method(
                id="owner_earnings",
                label="Owner Earnings",
                school=ValuationSchool.BUFFETT,
                unit=ValuationUnit.CURRENCY,
                inputs=oe_inputs,
                missing=["free_cash_flow"],
            )
        )
    else:
        methods.append(
            ValuationMethod(
                id="owner_earnings",
                label="Owner Earnings",
                school=ValuationSchool.BUFFETT,
                value=fcf,
                unit=ValuationUnit.CURRENCY,
                inputs=oe_inputs,
                detail="FCF proxy — D&A / maintenance CapEx unavailable",
            )
        )

    # FCF yield
    fy_inputs = ["free_cash_flow", "market_cap"]
    if fcf is None or m.market_cap is None or m.market_cap <= 0:
        missing = []
        if fcf is None:
            missing.append("free_cash_flow")
        if m.market_cap is None or m.market_cap <= 0:
            missing.append("positive market_cap")
        methods.append(
            _null_method(
                id="fcf_yield",
                label="FCF Yield",
                school=ValuationSchool.BUFFETT,
                unit=ValuationUnit.PERCENT,
                inputs=fy_inputs,
                missing=missing,
            )
        )
    else:
        methods.append(
            ValuationMethod(
                id="fcf_yield",
                label="FCF Yield",
                school=ValuationSchool.BUFFETT,
                value=fcf / m.market_cap,
                unit=ValuationUnit.PERCENT,
                inputs=fy_inputs,
                detail="FCF / market_cap",
            )
        )

    # ROIC — always null in T2
    methods.append(
        ValuationMethod(
            id="roic",
            label="ROIC",
            school=ValuationSchool.BUFFETT,
            value=None,
            unit=ValuationUnit.PERCENT,
            inputs=[],
            detail=f"{INSUFFICIENT_DATA}: EBIT / invested capital (always null in T2)",
        )
    )

    # Capital efficiency
    ce_inputs = ["free_cash_flow", "revenue_ttm"]
    if fcf is None or m.revenue_ttm is None or m.revenue_ttm <= 0:
        missing = []
        if fcf is None:
            missing.append("free_cash_flow")
        if m.revenue_ttm is None or m.revenue_ttm <= 0:
            missing.append("positive revenue_ttm")
        methods.append(
            _null_method(
                id="capital_efficiency",
                label="Capital Efficiency",
                school=ValuationSchool.BUFFETT,
                unit=ValuationUnit.RATIO,
                inputs=ce_inputs,
                missing=missing,
            )
        )
    else:
        methods.append(
            ValuationMethod(
                id="capital_efficiency",
                label="Capital Efficiency",
                school=ValuationSchool.BUFFETT,
                value=fcf / m.revenue_ttm,
                unit=ValuationUnit.RATIO,
                inputs=ce_inputs,
                detail="FCF / revenue",
            )
        )

    # Moat indicators (pass-through)
    for mid, label, field, val in (
        ("gross_margin", "Gross Margin", "gross_margin", m.gross_margin),
        ("operating_margin", "Operating Margin", "operating_margin", m.operating_margin),
    ):
        if val is None:
            methods.append(
                _null_method(
                    id=mid,
                    label=label,
                    school=ValuationSchool.BUFFETT,
                    unit=ValuationUnit.PERCENT,
                    inputs=[field],
                    missing=[field],
                )
            )
        else:
            methods.append(
                ValuationMethod(
                    id=mid,
                    label=label,
                    school=ValuationSchool.BUFFETT,
                    value=val,
                    unit=ValuationUnit.PERCENT,
                    inputs=[field],
                    detail="moat indicator (pass-through)",
                )
            )

    return methods


def _modern_methods(m: FinancialMetrics) -> tuple[list[ValuationMethod], float | None]:
    methods: list[ValuationMethod] = []
    fcf = _fcf(m)
    dcf_value: float | None = None

    # DCF Gordon
    dcf_inputs = ["free_cash_flow", "earnings_growth"]
    growth = m.earnings_growth if m.earnings_growth is not None else 0.0
    g = max(0.0, min(_DCF_GROWTH_CAP, growth))
    r = _DCF_DISCOUNT_RATE
    if fcf is None or fcf <= 0 or r <= g:
        missing = []
        if fcf is None or fcf <= 0:
            missing.append("positive free_cash_flow")
        if r <= g:
            missing.append("r > g")
        methods.append(
            _null_method(
                id="dcf",
                label="DCF (Gordon)",
                school=ValuationSchool.MODERN,
                unit=ValuationUnit.CURRENCY,
                inputs=dcf_inputs,
                missing=missing or ["positive free_cash_flow"],
            )
        )
    else:
        dcf_value = fcf * (1.0 + g) / (r - g)
        methods.append(
            ValuationMethod(
                id="dcf",
                label="DCF (Gordon)",
                school=ValuationSchool.MODERN,
                value=dcf_value,
                unit=ValuationUnit.CURRENCY,
                inputs=dcf_inputs,
                detail=f"FCF×(1+g)/(r−g) with r={r:.0%}, g={g:.0%}",
            )
        )

    # Reverse DCF
    rdcf_inputs = ["free_cash_flow", "market_cap"]
    if fcf is None or fcf <= 0 or m.market_cap is None or m.market_cap <= 0:
        missing = []
        if fcf is None or fcf <= 0:
            missing.append("positive free_cash_flow")
        if m.market_cap is None or m.market_cap <= 0:
            missing.append("positive market_cap")
        methods.append(
            _null_method(
                id="reverse_dcf",
                label="Reverse DCF",
                school=ValuationSchool.MODERN,
                unit=ValuationUnit.PERCENT,
                inputs=rdcf_inputs,
                missing=missing,
            )
        )
    else:
        implied_g = (m.market_cap * r - fcf) / (m.market_cap + fcf)
        methods.append(
            ValuationMethod(
                id="reverse_dcf",
                label="Reverse DCF",
                school=ValuationSchool.MODERN,
                value=implied_g,
                unit=ValuationUnit.PERCENT,
                inputs=rdcf_inputs,
                detail=f"implied g at r={r:.0%}",
            )
        )

    # EV/EBITDA
    if m.ev_to_ebitda is None:
        methods.append(
            _null_method(
                id="ev_ebitda",
                label="EV/EBITDA",
                school=ValuationSchool.MODERN,
                unit=ValuationUnit.MULTIPLE,
                inputs=["ev_to_ebitda"],
                missing=["ev_to_ebitda"],
            )
        )
    else:
        methods.append(
            ValuationMethod(
                id="ev_ebitda",
                label="EV/EBITDA",
                school=ValuationSchool.MODERN,
                value=m.ev_to_ebitda,
                unit=ValuationUnit.MULTIPLE,
                inputs=["ev_to_ebitda"],
                detail="pass-through",
            )
        )

    # EV/FCF
    evfcf_inputs = ["enterprise_value", "free_cash_flow"]
    if m.enterprise_value is None or fcf is None or fcf <= 0:
        missing = []
        if m.enterprise_value is None:
            missing.append("enterprise_value")
        if fcf is None or fcf <= 0:
            missing.append("positive free_cash_flow")
        methods.append(
            _null_method(
                id="ev_fcf",
                label="EV/FCF",
                school=ValuationSchool.MODERN,
                unit=ValuationUnit.MULTIPLE,
                inputs=evfcf_inputs,
                missing=missing,
            )
        )
    else:
        methods.append(
            ValuationMethod(
                id="ev_fcf",
                label="EV/FCF",
                school=ValuationSchool.MODERN,
                value=m.enterprise_value / fcf,
                unit=ValuationUnit.MULTIPLE,
                inputs=evfcf_inputs,
                detail="enterprise_value / FCF",
            )
        )

    # PEG
    if m.peg_ratio is None:
        methods.append(
            _null_method(
                id="peg",
                label="PEG",
                school=ValuationSchool.MODERN,
                unit=ValuationUnit.MULTIPLE,
                inputs=["peg_ratio"],
                missing=["peg_ratio"],
            )
        )
    else:
        methods.append(
            ValuationMethod(
                id="peg",
                label="PEG",
                school=ValuationSchool.MODERN,
                value=m.peg_ratio,
                unit=ValuationUnit.MULTIPLE,
                inputs=["peg_ratio"],
                detail="pass-through",
            )
        )

    # Historical bands — always null
    for mid, label in (
        ("hist_pe_bands", "Historical PE Bands"),
        ("hist_ps_bands", "Historical PS Bands"),
        ("hist_pb_bands", "Historical PB Bands"),
    ):
        methods.append(
            ValuationMethod(
                id=mid,
                label=label,
                school=ValuationSchool.MODERN,
                value=None,
                unit=ValuationUnit.MULTIPLE,
                inputs=[],
                detail=f"{INSUFFICIENT_DATA}: no historical multiples series",
            )
        )

    # Sector relative — always null
    methods.append(
        ValuationMethod(
            id="sector_relative",
            label="Sector Relative",
            school=ValuationSchool.MODERN,
            value=None,
            unit=ValuationUnit.RATIO,
            inputs=[],
            detail=f"{INSUFFICIENT_DATA}: no peer set",
        )
    )

    return methods, dcf_value


def _expected_fair(
    intrinsic: float | None,
    dcf: float | None,
    adjusted_book: float | None,
) -> float | None:
    vals = [v for v in (intrinsic, dcf, adjusted_book) if v is not None]
    if not vals:
        return None
    return float(median(vals))


def _mos_stars(mos: float) -> int:
    if mos >= 0.40:
        return 5
    if mos >= 0.30:
        return 4
    if mos >= 0.15:
        return 3
    if mos >= 0.0:
        return 2
    return 1


def _mos_rating(mos: float) -> str:
    if mos >= 0.30:
        return "Excellent"
    if mos >= 0.15:
        return "Good"
    if mos >= 0.0:
        return "Fair"
    return "Poor"


def margin_of_safety_for(m: FinancialMetrics) -> MarginOfSafetyView:
    """Intrinsic vs market price visualization (PRD §5.4.7)."""
    v, p, g = graham_intrinsic_per_share(m)
    if v is None or p is None:
        missing = []
        if m.eps_trailing is None or m.eps_trailing <= 0:
            missing.append("eps_trailing")
        if _pe(m) is None:
            missing.append("positive trailing P/E")
        return MarginOfSafetyView(
            detail=f"{INSUFFICIENT_DATA}: {', '.join(missing) or 'eps_trailing / P/E'}",
        )
    mos = (v - p) / v
    label = _mos_rating(mos)
    return MarginOfSafetyView(
        intrinsic_value=v,
        market_price=p,
        margin_of_safety=mos,
        stars=_mos_stars(mos),
        rating=f"{label} — {mos * 100.0:.0f}%",
        detail=f"intrinsic {v:.2f} vs price {p:.2f} (g={g:.0%})",
    )


def valuation_set_for(m: FinancialMetrics) -> ValuationSet:
    """Graham / Buffett / Modern methods + six-value ladder."""
    graham, firm_intrinsic, liquidation, adjusted_book = _graham_methods(m)
    buffett = _buffett_methods(m)
    modern, dcf_value = _modern_methods(m)

    ladder = ValuationLadder(
        market=m.market_cap,
        intrinsic=firm_intrinsic,
        liquidation=liquidation,
        replacement=None,  # PRD open Q — method unlocked
        enterprise=m.enterprise_value,
        expected_fair=_expected_fair(firm_intrinsic, dcf_value, adjusted_book),
    )
    return ValuationSet(
        graham=graham,
        buffett=buffett,
        modern=modern,
        ladder=ladder,
    )
