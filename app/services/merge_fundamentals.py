"""Merge multi-source FundamentalsSnapshot with field provenance (2C.3)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.schemas.financials import (
    FieldProvenance,
    FinancialMetrics,
    FundamentalsSnapshot,
    StatementSummary,
)
from app.services.source_registry import SOURCE_SEC_XBRL, SOURCE_YAHOO

# Relative tolerance for float disagreement (1%).
_FLOAT_RTOL = 0.01
_FLOAT_ATOL = 1e-9

# Statement / accounting fields — prefer SEC XBRL over Yahoo.
_STATEMENT_FIELDS = frozenset(
    {
        "balance_sheet",
        "cash_flow",
        "total_cash",
        "total_debt",
        "eps_trailing",
        "earnings_history",
        "revenue_history",
        "gross_margin",
        "operating_margin",
        "free_cash_flow",
        "debt_to_equity",
        "return_on_equity",
        "current_ratio",
    }
)

_SCALAR_FIELDS = (
    "market_cap",
    "revenue_growth",
    "gross_margin",
    "operating_margin",
    "free_cash_flow",
    "debt_to_equity",
    "pe_ratio",
    "trailing_pe",
    "forward_pe",
    "eps_trailing",
    "eps_forward",
    "earnings_growth",
    "return_on_equity",
    "current_ratio",
    "total_cash",
    "total_debt",
)

_STATEMENT_NESTED_FIELDS = (
    "as_of",
    "total_revenue",
    "net_income",
    "total_assets",
    "total_liabilities",
    "total_cash",
    "total_debt",
    "operating_cashflow",
    "free_cash_flow",
)


@dataclass(frozen=True)
class ProviderSnapshot:
    """One provider's fundamentals contribution."""

    source_id: str
    snapshot: FinancialMetrics


@dataclass
class FieldConflict:
    """Disagreement on one field across providers (deterministic)."""

    field_path: str
    chosen_source_id: str
    values: dict[str, Any]


@dataclass
class MergeFundamentalsResult:
    """Merged snapshot plus provenance and field conflicts."""

    snapshot: FundamentalsSnapshot
    conflicts: list[FieldConflict] = field(default_factory=list)
    sources_used: list[str] = field(default_factory=list)


def trust_rank(source_id: str, field_path: str) -> int:
    """Higher = preferred. Statement fields prefer SEC XBRL; market fields prefer Yahoo."""
    root = field_path.split(".", 1)[0]
    is_statement = root in _STATEMENT_FIELDS or field_path.startswith(
        ("balance_sheet.", "cash_flow.")
    )
    if is_statement:
        if source_id == SOURCE_SEC_XBRL:
            return 100
        if source_id == SOURCE_YAHOO:
            return 80
    else:
        if source_id == SOURCE_YAHOO:
            return 100
        if source_id == SOURCE_SEC_XBRL:
            return 70
    return 50


def _values_disagree(a: Any, b: Any) -> bool:
    if a is None or b is None:
        return False
    if isinstance(a, float) or isinstance(b, float):
        try:
            fa, fb = float(a), float(b)
        except (TypeError, ValueError):
            return a != b
        if abs(fa - fb) <= _FLOAT_ATOL:
            return False
        denom = max(abs(fa), abs(fb), _FLOAT_ATOL)
        return abs(fa - fb) / denom > _FLOAT_RTOL
    if isinstance(a, list) and isinstance(b, list):
        return a != b
    return a != b


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, list):
        return len(value) == 0
    return False


def merge_fundamentals(
    providers: list[ProviderSnapshot | None],
    *,
    ticker: str,
) -> MergeFundamentalsResult:
    """Fill-nulls by trust; on disagreement keep higher trust and record conflict.

    Never invents values. Empty provider list → empty ticker-only snapshot.
    """
    active = [p for p in providers if p is not None and p.snapshot is not None]
    sources_used = [p.source_id for p in active]
    if not active:
        return MergeFundamentalsResult(
            snapshot=FinancialMetrics(ticker=ticker, source_id="merged"),
            sources_used=[],
        )

    # Sort each field decision by trust at pick time.
    provenance: dict[str, FieldProvenance] = {}
    conflicts: list[FieldConflict] = []
    merged_data: dict[str, Any] = {"ticker": ticker}

    def _as_of_for(p: ProviderSnapshot) -> datetime | None:
        return p.snapshot.as_of

    def _consider(field_path: str, candidates: list[tuple[ProviderSnapshot, Any]]) -> Any:
        nonempty = [(p, v) for p, v in candidates if not _is_empty(v)]
        if not nonempty:
            return None
        nonempty.sort(key=lambda pv: trust_rank(pv[0].source_id, field_path), reverse=True)
        winner_p, winner_v = nonempty[0]
        value_map = {p.source_id: v for p, v in nonempty}
        for p, v in nonempty[1:]:
            if _values_disagree(winner_v, v):
                conflicts.append(
                    FieldConflict(
                        field_path=field_path,
                        chosen_source_id=winner_p.source_id,
                        values=value_map,
                    )
                )
                break
        provenance[field_path] = FieldProvenance(
            source_id=winner_p.source_id,
            as_of=_as_of_for(winner_p),
        )
        return winner_v

    for name in _SCALAR_FIELDS:
        chosen = _consider(
            name,
            [(p, getattr(p.snapshot, name)) for p in active],
        )
        merged_data[name] = chosen

    for name in ("profile", "returns"):
        chosen = _consider(
            name,
            [(p, getattr(p.snapshot, name)) for p in active],
        )
        merged_data[name] = chosen

    for name in ("revenue_history", "earnings_history"):
        chosen = _consider(
            name,
            [(p, getattr(p.snapshot, name)) for p in active],
        )
        merged_data[name] = chosen if chosen is not None else []

    for stmt_name in ("balance_sheet", "cash_flow"):
        nested: dict[str, Any] = {}
        any_nested = False
        for nested_field in _STATEMENT_NESTED_FIELDS:
            path = f"{stmt_name}.{nested_field}"
            candidates: list[tuple[ProviderSnapshot, Any]] = []
            for p in active:
                stmt = getattr(p.snapshot, stmt_name)
                val = getattr(stmt, nested_field) if stmt is not None else None
                candidates.append((p, val))
            chosen = _consider(path, candidates)
            nested[nested_field] = chosen
            if chosen is not None:
                any_nested = True
        if any_nested:
            merged_data[stmt_name] = StatementSummary(**nested)
            provenance[stmt_name] = FieldProvenance(
                source_id=provenance.get(
                    f"{stmt_name}.total_assets",
                    provenance.get(
                        f"{stmt_name}.operating_cashflow",
                        FieldProvenance(source_id=sources_used[0]),
                    ),
                ).source_id
            )
        else:
            merged_data[stmt_name] = None

    # Primary source_id: multi → merged; single → that source
    if len(sources_used) == 1:
        primary = sources_used[0]
    else:
        primary = "merged"

    as_of_candidates = [p.snapshot.as_of for p in active if p.snapshot.as_of]
    as_of = max(as_of_candidates) if as_of_candidates else None

    snapshot = FinancialMetrics(
        ticker=ticker,
        market_cap=merged_data.get("market_cap"),
        revenue_growth=merged_data.get("revenue_growth"),
        gross_margin=merged_data.get("gross_margin"),
        operating_margin=merged_data.get("operating_margin"),
        free_cash_flow=merged_data.get("free_cash_flow"),
        debt_to_equity=merged_data.get("debt_to_equity"),
        pe_ratio=merged_data.get("pe_ratio"),
        trailing_pe=merged_data.get("trailing_pe"),
        forward_pe=merged_data.get("forward_pe"),
        eps_trailing=merged_data.get("eps_trailing"),
        eps_forward=merged_data.get("eps_forward"),
        earnings_growth=merged_data.get("earnings_growth"),
        return_on_equity=merged_data.get("return_on_equity"),
        current_ratio=merged_data.get("current_ratio"),
        total_cash=merged_data.get("total_cash"),
        total_debt=merged_data.get("total_debt"),
        profile=merged_data.get("profile"),
        returns=merged_data.get("returns"),
        revenue_history=merged_data.get("revenue_history") or [],
        earnings_history=merged_data.get("earnings_history") or [],
        balance_sheet=merged_data.get("balance_sheet"),
        cash_flow=merged_data.get("cash_flow"),
        source_id=primary,
        as_of=as_of,
        field_provenance=provenance,
    )
    return MergeFundamentalsResult(
        snapshot=snapshot,
        conflicts=conflicts,
        sources_used=sources_used,
    )
