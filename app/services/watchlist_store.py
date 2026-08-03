"""Local JSON persistence for watchlist membership + summaries."""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.configs.settings import Settings, settings as default_settings
from app.schemas.ticker import InvalidTickerError, normalize_ticker
from app.schemas.watchlist import (
    ListKind,
    WatchlistMembership,
    WatchlistTickerSummary,
)

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()


def _default_doc() -> dict[str, Any]:
    return {"held": [], "watched": [], "summaries": {}}


def _path(app_settings: Settings | None = None) -> Path:
    s = app_settings if app_settings is not None else default_settings
    return Path(s.watchlist_path)


def load_raw(app_settings: Settings | None = None) -> dict[str, Any]:
    path = _path(app_settings)
    if not path.exists():
        return _default_doc()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            logger.warning("watchlist_corrupt path=%s reason=not_object", path)
            return _default_doc()
        held = data.get("held") or []
        watched = data.get("watched") or []
        summaries = data.get("summaries") or {}
        if not isinstance(held, list) or not isinstance(watched, list):
            return _default_doc()
        if not isinstance(summaries, dict):
            summaries = {}
        return {"held": list(held), "watched": list(watched), "summaries": summaries}
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        logger.warning("watchlist_corrupt path=%s err=%s", path, exc)
        return _default_doc()


def save_raw(doc: dict[str, Any], app_settings: Settings | None = None) -> None:
    path = _path(app_settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(doc, indent=2, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)


def normalize_membership(
    held: list[str],
    watched: list[str],
) -> WatchlistMembership:
    """Normalize tickers; held wins if listed in both."""
    held_norm: list[str] = []
    seen: set[str] = set()
    for raw in held:
        try:
            t = normalize_ticker(raw)
        except InvalidTickerError:
            continue
        if t not in seen:
            held_norm.append(t)
            seen.add(t)
    watched_norm: list[str] = []
    for raw in watched:
        try:
            t = normalize_ticker(raw)
        except InvalidTickerError:
            continue
        if t not in seen:
            watched_norm.append(t)
            seen.add(t)
    return WatchlistMembership(held=held_norm, watched=watched_norm)


def get_membership(app_settings: Settings | None = None) -> WatchlistMembership:
    doc = load_raw(app_settings)
    return normalize_membership(doc["held"], doc["watched"])


def put_membership(
    held: list[str],
    watched: list[str],
    app_settings: Settings | None = None,
) -> WatchlistMembership:
    membership = normalize_membership(held, watched)
    with _LOCK:
        doc = load_raw(app_settings)
        # Drop summaries for tickers no longer in membership
        keep = set(membership.held) | set(membership.watched)
        summaries = {
            k: v
            for k, v in (doc.get("summaries") or {}).items()
            if k in keep and isinstance(v, dict)
        }
        save_raw(
            {
                "held": membership.held,
                "watched": membership.watched,
                "summaries": summaries,
            },
            app_settings,
        )
    return membership


def list_kind_for(
    ticker: str,
    membership: WatchlistMembership | None = None,
    app_settings: Settings | None = None,
) -> ListKind | None:
    m = membership if membership is not None else get_membership(app_settings)
    t = ticker.upper()
    if t in m.held:
        return ListKind.HELD
    if t in m.watched:
        return ListKind.WATCHED
    return None


def upsert_summary(
    summary: WatchlistTickerSummary,
    app_settings: Settings | None = None,
) -> None:
    with _LOCK:
        doc = load_raw(app_settings)
        membership = normalize_membership(doc["held"], doc["watched"])
        kind = list_kind_for(summary.ticker, membership)
        if kind is None:
            # Still allow storing if caller knows membership; sync list_kind
            kind = summary.list_kind
            if kind == ListKind.HELD and summary.ticker not in membership.held:
                membership.held.append(summary.ticker)
            elif (
                kind == ListKind.WATCHED
                and summary.ticker not in membership.watched
            ):
                membership.watched.append(summary.ticker)
        payload = summary.model_copy(update={"list_kind": kind}).model_dump(
            mode="json"
        )
        summaries = dict(doc.get("summaries") or {})
        summaries[summary.ticker.upper()] = payload
        save_raw(
            {
                "held": membership.held,
                "watched": membership.watched,
                "summaries": summaries,
            },
            app_settings,
        )


def get_summaries(
    app_settings: Settings | None = None,
) -> list[WatchlistTickerSummary]:
    doc = load_raw(app_settings)
    membership = normalize_membership(doc["held"], doc["watched"])
    out: list[WatchlistTickerSummary] = []
    raw_summaries = doc.get("summaries") or {}
    order = list(membership.held) + list(membership.watched)
    for ticker in order:
        raw = raw_summaries.get(ticker)
        kind = (
            ListKind.HELD if ticker in membership.held else ListKind.WATCHED
        )
        if isinstance(raw, dict):
            try:
                data = dict(raw)
                data["ticker"] = ticker
                data["list_kind"] = kind.value
                out.append(WatchlistTickerSummary.model_validate(data))
                continue
            except Exception:  # noqa: BLE001
                logger.warning("watchlist_summary_corrupt ticker=%s", ticker)
        out.append(
            WatchlistTickerSummary(ticker=ticker, list_kind=kind)
        )
    return out


def add_ticker(
    ticker: str,
    list_kind: ListKind,
    app_settings: Settings | None = None,
) -> WatchlistMembership:
    t = normalize_ticker(ticker)
    m = get_membership(app_settings)
    held = [x for x in m.held if x != t]
    watched = [x for x in m.watched if x != t]
    if list_kind == ListKind.HELD:
        held.append(t)
    else:
        watched.append(t)
    return put_membership(held, watched, app_settings)


def remove_ticker(
    ticker: str,
    app_settings: Settings | None = None,
) -> WatchlistMembership:
    t = normalize_ticker(ticker)
    m = get_membership(app_settings)
    held = [x for x in m.held if x != t]
    watched = [x for x in m.watched if x != t]
    return put_membership(held, watched, app_settings)


@dataclass
class BulkMembershipResult:
    """Outcome of bulk remove / move (membership-only)."""

    affected: list[str] = field(default_factory=list)
    skipped_not_found: list[str] = field(default_factory=list)
    skipped_noop: list[str] = field(default_factory=list)
    membership: WatchlistMembership = field(
        default_factory=WatchlistMembership
    )


def _normalize_bulk_tickers(tickers: list[str]) -> list[str]:
    """Normalize and dedupe; raises InvalidTickerError on first bad symbol."""
    out: list[str] = []
    seen: set[str] = set()
    for raw in tickers:
        t = normalize_ticker(raw)
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def bulk_remove(
    tickers: list[str],
    app_settings: Settings | None = None,
) -> BulkMembershipResult:
    """Remove many tickers from Held ∪ Watched in one write."""
    normalized = _normalize_bulk_tickers(tickers)
    m = get_membership(app_settings)
    existing = set(m.held) | set(m.watched)
    affected: list[str] = []
    skipped_not_found: list[str] = []
    for t in normalized:
        if t in existing:
            affected.append(t)
        else:
            skipped_not_found.append(t)
    drop = set(affected)
    held = [x for x in m.held if x not in drop]
    watched = [x for x in m.watched if x not in drop]
    membership = (
        put_membership(held, watched, app_settings) if affected else m
    )
    return BulkMembershipResult(
        affected=affected,
        skipped_not_found=skipped_not_found,
        skipped_noop=[],
        membership=membership,
    )


def bulk_move(
    tickers: list[str],
    list_kind: ListKind,
    app_settings: Settings | None = None,
) -> BulkMembershipResult:
    """Move member tickers to Held or Watched; ignore unknowns; noop if already there."""
    normalized = _normalize_bulk_tickers(tickers)
    m = get_membership(app_settings)
    held_set = set(m.held)
    watched_set = set(m.watched)
    existing = held_set | watched_set
    target_set = held_set if list_kind == ListKind.HELD else watched_set

    affected: list[str] = []
    skipped_not_found: list[str] = []
    skipped_noop: list[str] = []
    for t in normalized:
        if t not in existing:
            skipped_not_found.append(t)
            continue
        if t in target_set:
            skipped_noop.append(t)
            continue
        affected.append(t)

    if not affected:
        return BulkMembershipResult(
            affected=[],
            skipped_not_found=skipped_not_found,
            skipped_noop=skipped_noop,
            membership=m,
        )

    move_set = set(affected)
    held = [x for x in m.held if x not in move_set]
    watched = [x for x in m.watched if x not in move_set]
    if list_kind == ListKind.HELD:
        held.extend(affected)
    else:
        watched.extend(affected)
    membership = put_membership(held, watched, app_settings)
    return BulkMembershipResult(
        affected=affected,
        skipped_not_found=skipped_not_found,
        skipped_noop=skipped_noop,
        membership=membership,
    )


def now_utc() -> datetime:
    return datetime.now(timezone.utc)
