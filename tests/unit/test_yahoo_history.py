"""Yahoo history helpers — daily return + move_score (Brief/Risk shared)."""

from __future__ import annotations

from pathlib import Path

from app.configs.settings import Settings
from app.services.source_cache import source_cache_store
from app.services.source_registry import SOURCE_YAHOO
from app.services.yahoo_history import (
    MOVE_GATE_ABS,
    daily_returns,
    last_session_daily_return,
    lookup_history_closes,
    move_score,
    parse_history_closes,
    passes_move_gate,
)


def test_parse_history_closes_tuples_and_dicts() -> None:
    payload = {
        "history_closes": [
            ["2024-01-02", 100.0],
            {"date": "2024-01-03", "close": 110.0},
            ["bad"],
            ["2024-01-04", -1],
        ]
    }
    closes = parse_history_closes(payload)
    assert closes == [("2024-01-02", 100.0), ("2024-01-03", 110.0)]


def test_last_session_daily_return_and_gate() -> None:
    closes = [("2024-01-02", 100.0), ("2024-01-03", 106.0)]
    ret = last_session_daily_return(closes)
    assert ret is not None
    assert abs(ret - 0.06) < 1e-9
    assert passes_move_gate(ret)
    assert move_score(ret) == 2  # 6% → 2

    assert not passes_move_gate(0.04)
    assert move_score(0.15) == 5
    assert move_score(0.12) == 4
    assert move_score(0.08) == 3
    assert move_score(0.0) == 0
    assert move_score(None) is None
    assert MOVE_GATE_ABS == 0.05


def test_daily_returns_map() -> None:
    closes = [
        ("2024-01-03", 110.0),
        ("2024-01-02", 100.0),
        ("2024-01-04", 99.0),
    ]
    rets = daily_returns(closes)
    assert abs(rets["2024-01-03"] - 0.10) < 1e-9
    assert abs(rets["2024-01-04"] - (-11.0 / 110.0)) < 1e-9


def test_lookup_from_yahoo_source_cache(tmp_path: Path) -> None:
    s = Settings(
        watchlist_path=tmp_path / "w.json",
        source_cache_dir=tmp_path / "sources",
        phase0_cache_dir=tmp_path / "phase0",
        brief_store_path=tmp_path / "briefs.json",
        brief_miss_log_path=tmp_path / "misses.jsonl",
    )
    source_cache_store(
        SOURCE_YAHOO,
        "NVDA",
        {
            "ticker": "NVDA",
            "history_closes": [["2024-06-01", 100.0], ["2024-06-02", 110.0]],
        },
        cache_root=s.source_cache_dir,
        app_settings=s,
    )
    closes = lookup_history_closes("NVDA", app_settings=s)
    assert closes is not None
    assert last_session_daily_return(closes) == 0.1
