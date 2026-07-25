"""2C.3 minimum fundamentals checklist (editable).

Before Yahoo-fatal softens to ``partial``, the merged ``FundamentalsSnapshot``
must satisfy every path in ``MINIMUM_FUNDAMENTALS_FIELD_PATHS``.

**How to change the bar:** add or remove dotted paths in that frozenset.
Nested fields use ``parent.child`` (e.g. ``balance_sheet.total_assets``).
Lists must be non-empty; other values must be non-``None``.

Locked from founder dogfood (2026-07-25). Revisit as we learn which fields
SEC XBRL / merge can reliably fill.
"""

from __future__ import annotations

from typing import Any

from app.schemas.financials import FinancialMetrics, FundamentalsSnapshot

# --- edit this set to raise/lower the soften-Yahoo bar ---
MINIMUM_FUNDAMENTALS_FIELD_PATHS: frozenset[str] = frozenset(
    {
        # Objects / series (must be present; lists non-empty)
        "balance_sheet",
        "cash_flow",
        "earnings_history",
        # Top-level scalars (market P/E / forward EPS trimmed for now —
        # SEC XBRL cannot fill them; may re-add when AV/FMP lands)
        "gross_margin",
        "operating_margin",
        "total_debt",
        "total_cash",
        "eps_trailing",
        # Nested on balance_sheet (statement truth)
        "balance_sheet.total_revenue",
        "balance_sheet.total_assets",
        "balance_sheet.total_liabilities",
        "balance_sheet.total_cash",
        "balance_sheet.total_debt",
    }
)


def _resolve_path(root: Any, path: str) -> Any:
    cur: Any = root
    for part in path.split("."):
        if cur is None:
            return None
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            cur = getattr(cur, part, None)
    return cur


def _path_satisfied(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, list):
        return len(value) > 0
    return True


def missing_minimum_fundamentals(
    snapshot: FinancialMetrics | FundamentalsSnapshot | None,
) -> list[str]:
    """Return sorted field paths that fail the minimum checklist."""
    if snapshot is None:
        return sorted(MINIMUM_FUNDAMENTALS_FIELD_PATHS)
    missing = [
        path
        for path in MINIMUM_FUNDAMENTALS_FIELD_PATHS
        if not _path_satisfied(_resolve_path(snapshot, path))
    ]
    return sorted(missing)


def has_minimum_fundamentals(
    snapshot: FinancialMetrics | FundamentalsSnapshot | None,
) -> bool:
    """True when merged snapshot is rich enough to soften Yahoo-fatal → partial."""
    return not missing_minimum_fundamentals(snapshot)
