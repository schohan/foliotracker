"""Local persistence for DailyBrief ring + miss log (watchlist_store pattern)."""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.configs.settings import Settings, settings as default_settings
from app.schemas.brief import DailyBrief

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()
DEFAULT_RING_SIZE = 14


def _briefs_path(app_settings: Settings | None = None) -> Path:
    s = app_settings if app_settings is not None else default_settings
    return Path(s.brief_store_path)


def _miss_log_path(app_settings: Settings | None = None) -> Path:
    s = app_settings if app_settings is not None else default_settings
    return Path(s.brief_miss_log_path)


def _default_doc() -> dict[str, Any]:
    return {"briefs": []}


def load_raw(app_settings: Settings | None = None) -> dict[str, Any]:
    path = _briefs_path(app_settings)
    if not path.exists():
        return _default_doc()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return _default_doc()
        briefs = data.get("briefs") or []
        if not isinstance(briefs, list):
            return _default_doc()
        return {"briefs": briefs}
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        logger.warning("brief_store_corrupt path=%s err=%s", path, exc)
        return _default_doc()


def save_raw(doc: dict[str, Any], app_settings: Settings | None = None) -> None:
    path = _briefs_path(app_settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(doc, indent=2, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)


def save_brief(
    brief: DailyBrief,
    *,
    app_settings: Settings | None = None,
    ring_size: int | None = None,
) -> DailyBrief:
    """Prepend brief into ring buffer (newest first)."""
    s = app_settings if app_settings is not None else default_settings
    n = ring_size if ring_size is not None else s.brief_ring_size
    payload = brief.model_dump(mode="json")
    with _LOCK:
        doc = load_raw(s)
        briefs = [payload] + list(doc.get("briefs") or [])
        doc["briefs"] = briefs[: max(1, n)]
        save_raw(doc, s)
    return brief


def get_latest_brief(app_settings: Settings | None = None) -> DailyBrief | None:
    doc = load_raw(app_settings)
    briefs = doc.get("briefs") or []
    if not briefs:
        return None
    try:
        return DailyBrief.model_validate(briefs[0])
    except Exception as exc:  # noqa: BLE001
        logger.warning("brief_latest_invalid err=%s", exc)
        return None


def list_briefs(
    *,
    app_settings: Settings | None = None,
    limit: int = 14,
) -> list[DailyBrief]:
    doc = load_raw(app_settings)
    out: list[DailyBrief] = []
    for raw in (doc.get("briefs") or [])[:limit]:
        try:
            out.append(DailyBrief.model_validate(raw))
        except Exception:  # noqa: BLE001
            continue
    return out


def append_miss_note(
    note: str,
    *,
    app_settings: Settings | None = None,
) -> dict[str, str]:
    """Append a dogfood miss note (JSONL)."""
    s = app_settings if app_settings is not None else default_settings
    path = _miss_log_path(s)
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "note": note.strip(),
    }
    with _LOCK:
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
    return entry
