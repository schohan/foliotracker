"""SEC XBRL companyfacts parse tests."""

from __future__ import annotations

from app.tools.filings.sec_xbrl import parse_companyfacts_json


def _fact(val: float, *, end: str, filed: str, form: str = "10-K", start: str | None = None) -> dict:
    row = {
        "val": val,
        "end": end,
        "filed": filed,
        "form": form,
        "fy": int(end[:4]),
        "fp": "FY" if form.startswith("10-K") else "Q1",
    }
    if start is not None:
        row["start"] = start
    return row


def _concept(*rows: dict) -> dict:
    return {"label": "x", "units": {"USD": list(rows)}}


def test_parse_companyfacts_maps_statements() -> None:
    payload = {
        "cik": 320193,
        "entityName": "Apple Inc.",
        "facts": {
            "us-gaap": {
                "RevenueFromContractWithCustomerExcludingAssessedTax": _concept(
                    _fact(
                        100.0,
                        end="2024-09-28",
                        filed="2024-11-01",
                        start="2023-10-01",
                    )
                ),
                "NetIncomeLoss": _concept(
                    _fact(
                        20.0,
                        end="2024-09-28",
                        filed="2024-11-01",
                        start="2023-10-01",
                    ),
                    _fact(
                        18.0,
                        end="2023-09-30",
                        filed="2023-11-03",
                        start="2022-10-01",
                    ),
                ),
                "Assets": _concept(
                    _fact(500.0, end="2024-09-28", filed="2024-11-01")
                ),
                "Liabilities": _concept(
                    _fact(200.0, end="2024-09-28", filed="2024-11-01")
                ),
                "CashAndCashEquivalentsAtCarryingValue": _concept(
                    _fact(50.0, end="2024-09-28", filed="2024-11-01")
                ),
                "LongTermDebt": _concept(
                    _fact(80.0, end="2024-09-28", filed="2024-11-01")
                ),
                "GrossProfit": _concept(
                    _fact(
                        40.0,
                        end="2024-09-28",
                        filed="2024-11-01",
                        start="2023-10-01",
                    )
                ),
                "OperatingIncomeLoss": _concept(
                    _fact(
                        30.0,
                        end="2024-09-28",
                        filed="2024-11-01",
                        start="2023-10-01",
                    )
                ),
                "NetCashProvidedByUsedInOperatingActivities": _concept(
                    _fact(
                        25.0,
                        end="2024-09-28",
                        filed="2024-11-01",
                        start="2023-10-01",
                    )
                ),
                "EarningsPerShareDiluted": _concept(
                    _fact(
                        6.5,
                        end="2024-09-28",
                        filed="2024-11-01",
                        start="2023-10-01",
                    )
                ),
            }
        },
    }
    m = parse_companyfacts_json(payload, ticker="AAPL")
    assert m.ticker == "AAPL"
    assert m.source_id == "sec_xbrl"
    assert m.balance_sheet is not None
    assert m.balance_sheet.total_assets == 500.0
    assert m.balance_sheet.total_liabilities == 200.0
    assert m.balance_sheet.total_cash == 50.0
    assert m.balance_sheet.total_debt == 80.0
    assert m.balance_sheet.total_revenue == 100.0
    assert m.cash_flow is not None
    assert m.cash_flow.operating_cashflow == 25.0
    assert m.gross_margin == 0.4
    assert m.operating_margin == 0.3
    assert m.eps_trailing == 6.5
    assert m.total_cash == 50.0
    assert m.total_debt == 80.0
    assert len(m.earnings_history) >= 1
    # Market fields stay empty (Yahoo / AV)
    assert m.pe_ratio is None
    assert m.forward_pe is None
    assert m.eps_forward is None


def test_parse_prefers_revenue_tag_fallback() -> None:
    payload = {
        "entityName": "Test Co",
        "facts": {
            "us-gaap": {
                "Revenues": _concept(
                    _fact(
                        10.0,
                        end="2024-12-31",
                        filed="2025-02-01",
                        start="2024-01-01",
                    )
                ),
                "Assets": _concept(
                    _fact(1.0, end="2024-12-31", filed="2025-02-01")
                ),
            }
        },
    }
    m = parse_companyfacts_json(payload, ticker="TEST")
    assert m.balance_sheet is not None
    assert m.balance_sheet.total_revenue == 10.0
