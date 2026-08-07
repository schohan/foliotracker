"""Net Asset Intelligence T2 — asset breakdown → adjusted net assets vs market.

Implements the locked Net Asset Intelligence table in architecture.md
"Valuation / net-asset formula specs" (2026-08-07). Pure Python; line items
without source fields stay ``null`` (honest gaps).
"""

from __future__ import annotations

from app.schemas.financials import FinancialMetrics
from app.schemas.thesis import (
    INSUFFICIENT_DATA,
    AssetBreakdown,
    AssetLine,
    AssetVerdict,
)

# Fair band around zero difference (±5%).
_FAIR_BAND = 0.05

# Fixed line order for UI (PRD §5.4.6 reference).
_ASSET_NAMES = (
    "Cash",
    "Receivables",
    "Inventory",
    "Factories",
    "Land",
    "Investments",
    "Patents",
    "Other Assets",
)
_LIABILITY_NAMES = (
    "Total Debt",
    "Lease",
    "Other Liabilities",
)


def asset_breakdown_for(m: FinancialMetrics) -> AssetBreakdown:
    """Assets − liabilities → Adjusted Net Assets vs market cap."""
    bs = m.balance_sheet
    total_assets = bs.total_assets if bs is not None else None
    total_liabilities = bs.total_liabilities if bs is not None else None
    cash = m.total_cash
    if cash is None and bs is not None:
        cash = bs.total_cash
    total_debt = m.total_debt
    if total_debt is None and bs is not None:
        total_debt = bs.total_debt

    other_assets: float | None = None
    if total_assets is not None and cash is not None:
        other_assets = total_assets - cash

    other_liabilities: float | None = None
    if total_liabilities is not None and total_debt is not None:
        other_liabilities = total_liabilities - total_debt

    asset_values: dict[str, float | None] = {
        "Cash": cash,
        "Receivables": None,
        "Inventory": None,
        "Factories": None,
        "Land": None,
        "Investments": None,
        "Patents": None,
        "Other Assets": other_assets,
    }
    liability_values: dict[str, float | None] = {
        "Total Debt": total_debt,
        "Lease": None,
        "Other Liabilities": other_liabilities,
    }

    assets = [AssetLine(name=n, value=asset_values[n]) for n in _ASSET_NAMES]
    liabilities = [
        AssetLine(name=n, value=liability_values[n]) for n in _LIABILITY_NAMES
    ]

    adjusted: float | None = None
    if total_assets is not None and total_liabilities is not None:
        adjusted = total_assets - total_liabilities

    market = m.market_cap
    difference_pct: float | None = None
    verdict: AssetVerdict | None = None
    detail = ""

    if adjusted is None:
        detail = f"{INSUFFICIENT_DATA}: balance_sheet.total_assets / total_liabilities"
    elif market is None:
        detail = f"{INSUFFICIENT_DATA}: market_cap"
    elif adjusted == 0:
        detail = f"{INSUFFICIENT_DATA}: adjusted_net_assets is zero"
    else:
        difference_pct = (market - adjusted) / adjusted
        if difference_pct < -_FAIR_BAND:
            verdict = AssetVerdict.POSSIBLE_UNDERVALUATION
        elif difference_pct > _FAIR_BAND:
            verdict = AssetVerdict.POSSIBLE_OVERVALUATION
        else:
            verdict = AssetVerdict.FAIR
        detail = f"difference {(difference_pct * 100.0):.0f}% vs adjusted net assets"

    return AssetBreakdown(
        assets=assets,
        liabilities=liabilities,
        adjusted_net_assets=adjusted,
        market_cap=market,
        difference_pct=difference_pct,
        verdict=verdict,
        detail=detail,
    )
