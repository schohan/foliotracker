"""Local TTL file cache for Phase0Result."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.schemas.evidence import BundleStatus, Evidence, EvidenceBundle
from app.schemas.phase0 import Phase0Result, Phase0Status
from app.schemas.report import InvestmentThesis, ThesisClaim
from app.services.phase0_cache import cache_lookup, cache_store


def _ok_result(ticker: str = "NVDA", request_id: str = "req-orig") -> Phase0Result:
    eid = f"ev_financial_{ticker}_1"
    bundle = EvidenceBundle(
        ticker=ticker,
        status=BundleStatus.OK,
        items=[
            Evidence(
                id=eid,
                type="financial",
                source="Yahoo Finance",
                confidence=0.95,
                timestamp=datetime.now(timezone.utc),
                data={"pe_ratio": 25.0},
            )
        ],
    )
    thesis = InvestmentThesis(
        ticker=ticker,
        thesis="Cached thesis.",
        claims=[ThesisClaim(text="PE is 25.", evidence_ids=[eid])],
    )
    return Phase0Result(
        ticker=ticker,
        status=Phase0Status.OK,
        evidence=bundle,
        thesis=thesis,
        request_id=request_id,
        cache_hit=False,
    )


def test_cache_miss_then_store_then_hit(tmp_path: Path) -> None:
    ticker = "NVDA"
    assert cache_lookup(ticker, cache_dir=tmp_path, ttl_seconds=3600) is None

    stored = _ok_result()
    cache_store(stored, cache_dir=tmp_path)

    hit = cache_lookup(ticker, cache_dir=tmp_path, ttl_seconds=3600)
    assert hit is not None
    assert hit.cache_hit is True
    assert hit.ticker == "NVDA"
    assert hit.request_id != stored.request_id


def test_cache_expired_is_miss(tmp_path: Path) -> None:
    stored = _ok_result()
    cache_store(stored, cache_dir=tmp_path)
    assert cache_lookup("NVDA", cache_dir=tmp_path, ttl_seconds=0) is None


def test_cache_corrupt_file_is_miss(tmp_path: Path) -> None:
    bad = tmp_path / "NVDA.json"
    bad.write_text("{not-json", encoding="utf-8")
    assert cache_lookup("NVDA", cache_dir=tmp_path, ttl_seconds=3600) is None


def test_cache_never_stores_error(tmp_path: Path) -> None:
    err = Phase0Result(
        ticker="NVDA",
        status=Phase0Status.ERROR,
        error_message="fail",
        request_id="req-err",
        cache_hit=False,
    )
    cache_store(err, cache_dir=tmp_path)
    assert cache_lookup("NVDA", cache_dir=tmp_path, ttl_seconds=3600) is None
