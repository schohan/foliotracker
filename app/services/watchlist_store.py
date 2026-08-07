"""Local JSON persistence for watchlist membership + summaries + collections."""

from __future__ import annotations

import json
import logging
import re
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.configs.settings import Settings, settings as default_settings
from app.schemas.ticker import InvalidTickerError, normalize_ticker
from app.schemas.watchlist import (
    ListKind,
    WatchlistCollection,
    WatchlistMembership,
    WatchlistTickerSummary,
)

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()
_COLLECTION_NAME_RE = re.compile(r"^[\w][\w \-'&.]{0,39}$", re.UNICODE)
_MAX_COLLECTION_NAME = 40


class CollectionError(Exception):
    """Base for collection validation / lookup errors."""


class CollectionNotFoundError(CollectionError):
    """Unknown collection id."""


class CollectionNameError(CollectionError):
    """Invalid or duplicate collection name."""


def _default_doc() -> dict[str, Any]:
    return {"held": [], "watched": [], "summaries": {}, "collections": []}


def _path(app_settings: Settings | None = None) -> Path:
    s = app_settings if app_settings is not None else default_settings
    return Path(s.watchlist_path)


def _normalize_collection_name(name: str) -> str:
    cleaned = " ".join((name or "").split())
    if not cleaned or len(cleaned) > _MAX_COLLECTION_NAME:
        raise CollectionNameError(
            f"Collection name must be 1–{_MAX_COLLECTION_NAME} characters"
        )
    if not _COLLECTION_NAME_RE.match(cleaned):
        raise CollectionNameError(
            "Collection name may use letters, numbers, spaces, and -_'&."
        )
    return cleaned


def _parse_collections(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        cid = item.get("id")
        name = item.get("name")
        tickers_raw = item.get("tickers") or []
        if not isinstance(cid, str) or not cid:
            continue
        if not isinstance(name, str) or not name.strip():
            continue
        tickers: list[str] = []
        seen: set[str] = set()
        if isinstance(tickers_raw, list):
            for t in tickers_raw:
                if not isinstance(t, str):
                    continue
                try:
                    n = normalize_ticker(t)
                except InvalidTickerError:
                    continue
                if n not in seen:
                    seen.add(n)
                    tickers.append(n)
        out.append({"id": cid, "name": name.strip(), "tickers": tickers})
    return out


def _collections_as_models(raw: list[dict[str, Any]]) -> list[WatchlistCollection]:
    return [
        WatchlistCollection(id=c["id"], name=c["name"], tickers=list(c["tickers"]))
        for c in raw
    ]


def _prune_collections(
    collections: list[dict[str, Any]],
    keep: set[str],
) -> list[dict[str, Any]]:
    pruned: list[dict[str, Any]] = []
    for c in collections:
        tickers = [t for t in c["tickers"] if t in keep]
        pruned.append({**c, "tickers": tickers})
    return pruned


def _doc_payload(
    membership: WatchlistMembership,
    summaries: dict[str, Any],
    collections: list[dict[str, Any]],
) -> dict[str, Any]:
    keep = set(membership.held) | set(membership.watched)
    return {
        "held": membership.held,
        "watched": membership.watched,
        "summaries": summaries,
        "collections": _prune_collections(collections, keep),
    }


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
        collections = _parse_collections(data.get("collections"))
        return {
            "held": list(held),
            "watched": list(watched),
            "summaries": summaries,
            "collections": collections,
        }
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


def list_collections(
    app_settings: Settings | None = None,
) -> list[WatchlistCollection]:
    doc = load_raw(app_settings)
    membership = normalize_membership(doc["held"], doc["watched"])
    keep = set(membership.held) | set(membership.watched)
    return _collections_as_models(
        _prune_collections(doc.get("collections") or [], keep)
    )


def put_membership(
    held: list[str],
    watched: list[str],
    app_settings: Settings | None = None,
) -> WatchlistMembership:
    membership = normalize_membership(held, watched)
    with _LOCK:
        doc = load_raw(app_settings)
        keep = set(membership.held) | set(membership.watched)
        summaries = {
            k: v
            for k, v in (doc.get("summaries") or {}).items()
            if k in keep and isinstance(v, dict)
        }
        collections = _prune_collections(doc.get("collections") or [], keep)
        save_raw(
            _doc_payload(membership, summaries, collections),
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
        collections = list(doc.get("collections") or [])
        save_raw(
            _doc_payload(membership, summaries, collections),
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


@dataclass
class CollectionMembersResult:
    """Outcome of add/remove tickers on a collection overlay."""

    affected: list[str] = field(default_factory=list)
    skipped_not_found: list[str] = field(default_factory=list)
    skipped_noop: list[str] = field(default_factory=list)
    collection: WatchlistCollection = field(
        default_factory=lambda: WatchlistCollection(id="", name="")
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


def _find_collection_index(
    collections: list[dict[str, Any]],
    collection_id: str,
) -> int:
    for i, c in enumerate(collections):
        if c["id"] == collection_id:
            return i
    raise CollectionNotFoundError(f"Collection not found: {collection_id}")


def _assert_unique_name(
    collections: list[dict[str, Any]],
    name: str,
    *,
    exclude_id: str | None = None,
) -> None:
    key = name.casefold()
    for c in collections:
        if exclude_id is not None and c["id"] == exclude_id:
            continue
        if str(c["name"]).casefold() == key:
            raise CollectionNameError(f"Collection already exists: {c['name']}")


def create_collection(
    name: str,
    app_settings: Settings | None = None,
) -> WatchlistCollection:
    cleaned = _normalize_collection_name(name)
    with _LOCK:
        doc = load_raw(app_settings)
        collections = list(doc.get("collections") or [])
        _assert_unique_name(collections, cleaned)
        cid = f"c_{uuid.uuid4().hex[:8]}"
        entry = {"id": cid, "name": cleaned, "tickers": []}
        collections.append(entry)
        membership = normalize_membership(doc["held"], doc["watched"])
        save_raw(
            _doc_payload(
                membership,
                dict(doc.get("summaries") or {}),
                collections,
            ),
            app_settings,
        )
    return WatchlistCollection(id=cid, name=cleaned, tickers=[])


def rename_collection(
    collection_id: str,
    name: str,
    app_settings: Settings | None = None,
) -> WatchlistCollection:
    cleaned = _normalize_collection_name(name)
    with _LOCK:
        doc = load_raw(app_settings)
        collections = list(doc.get("collections") or [])
        idx = _find_collection_index(collections, collection_id)
        _assert_unique_name(collections, cleaned, exclude_id=collection_id)
        collections[idx] = {**collections[idx], "name": cleaned}
        membership = normalize_membership(doc["held"], doc["watched"])
        keep = set(membership.held) | set(membership.watched)
        collections = _prune_collections(collections, keep)
        save_raw(
            _doc_payload(
                membership,
                dict(doc.get("summaries") or {}),
                collections,
            ),
            app_settings,
        )
        entry = collections[idx]
    return WatchlistCollection(
        id=entry["id"],
        name=entry["name"],
        tickers=list(entry["tickers"]),
    )


def delete_collection(
    collection_id: str,
    app_settings: Settings | None = None,
) -> None:
    with _LOCK:
        doc = load_raw(app_settings)
        collections = list(doc.get("collections") or [])
        idx = _find_collection_index(collections, collection_id)
        collections.pop(idx)
        membership = normalize_membership(doc["held"], doc["watched"])
        save_raw(
            _doc_payload(
                membership,
                dict(doc.get("summaries") or {}),
                collections,
            ),
            app_settings,
        )


def collection_add_tickers(
    collection_id: str,
    tickers: list[str],
    app_settings: Settings | None = None,
) -> CollectionMembersResult:
    normalized = _normalize_bulk_tickers(tickers)
    with _LOCK:
        doc = load_raw(app_settings)
        membership = normalize_membership(doc["held"], doc["watched"])
        existing = set(membership.held) | set(membership.watched)
        collections = list(doc.get("collections") or [])
        idx = _find_collection_index(collections, collection_id)
        current = list(collections[idx]["tickers"])
        current_set = set(current)

        affected: list[str] = []
        skipped_not_found: list[str] = []
        skipped_noop: list[str] = []
        for t in normalized:
            if t not in existing:
                skipped_not_found.append(t)
                continue
            if t in current_set:
                skipped_noop.append(t)
                continue
            current.append(t)
            current_set.add(t)
            affected.append(t)

        collections[idx] = {**collections[idx], "tickers": current}
        collections = _prune_collections(collections, existing)
        save_raw(
            _doc_payload(
                membership,
                dict(doc.get("summaries") or {}),
                collections,
            ),
            app_settings,
        )
        entry = collections[idx]
    return CollectionMembersResult(
        affected=affected,
        skipped_not_found=skipped_not_found,
        skipped_noop=skipped_noop,
        collection=WatchlistCollection(
            id=entry["id"],
            name=entry["name"],
            tickers=list(entry["tickers"]),
        ),
    )


def collection_remove_tickers(
    collection_id: str,
    tickers: list[str],
    app_settings: Settings | None = None,
) -> CollectionMembersResult:
    normalized = _normalize_bulk_tickers(tickers)
    with _LOCK:
        doc = load_raw(app_settings)
        membership = normalize_membership(doc["held"], doc["watched"])
        existing = set(membership.held) | set(membership.watched)
        collections = list(doc.get("collections") or [])
        idx = _find_collection_index(collections, collection_id)
        current = list(collections[idx]["tickers"])
        current_set = set(current)

        affected: list[str] = []
        skipped_not_found: list[str] = []
        skipped_noop: list[str] = []
        for t in normalized:
            if t not in current_set:
                skipped_not_found.append(t)
                continue
            affected.append(t)

        drop = set(affected)
        collections[idx] = {
            **collections[idx],
            "tickers": [t for t in current if t not in drop],
        }
        collections = _prune_collections(collections, existing)
        save_raw(
            _doc_payload(
                membership,
                dict(doc.get("summaries") or {}),
                collections,
            ),
            app_settings,
        )
        entry = collections[idx]
    return CollectionMembersResult(
        affected=affected,
        skipped_not_found=skipped_not_found,
        skipped_noop=skipped_noop,
        collection=WatchlistCollection(
            id=entry["id"],
            name=entry["name"],
            tickers=list(entry["tickers"]),
        ),
    )


def now_utc() -> datetime:
    return datetime.now(timezone.utc)
