"""Local persistence for ThesisDashboard ring + per-ticker snapshot rings."""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any

from app.configs.settings import Settings, settings as default_settings
from app.schemas.thesis import ThesisDashboard, ThesisSnapshot

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()


def _store_path(app_settings: Settings | None = None) -> Path:
    s = app_settings if app_settings is not None else default_settings
    return Path(s.thesis_store_path)


def _default_doc() -> dict[str, Any]:
    return {"dashboards": [], "snapshots": {}}


def load_raw(app_settings: Settings | None = None) -> dict[str, Any]:
    path = _store_path(app_settings)
    if not path.exists():
        return _default_doc()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return _default_doc()
        dashboards = data.get("dashboards") or []
        if not isinstance(dashboards, list):
            dashboards = []
        snapshots = data.get("snapshots") or {}
        if not isinstance(snapshots, dict):
            snapshots = {}
        return {"dashboards": dashboards, "snapshots": snapshots}
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        logger.warning("thesis_store_corrupt path=%s err=%s", path, exc)
        return _default_doc()


def save_raw(doc: dict[str, Any], app_settings: Settings | None = None) -> None:
    path = _store_path(app_settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Preserve both rings.
    out = {
        "dashboards": list(doc.get("dashboards") or []),
        "snapshots": dict(doc.get("snapshots") or {}),
    }
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(out, indent=2, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)


def save_dashboard(
    dashboard: ThesisDashboard,
    *,
    app_settings: Settings | None = None,
    ring_size: int | None = None,
) -> ThesisDashboard:
    """Prepend dashboard into ring buffer (newest first)."""
    s = app_settings if app_settings is not None else default_settings
    n = ring_size if ring_size is not None else s.thesis_ring_size
    payload = dashboard.model_dump(mode="json")
    with _LOCK:
        doc = load_raw(s)
        dashboards = [payload] + list(doc.get("dashboards") or [])
        doc["dashboards"] = dashboards[: max(1, n)]
        save_raw(doc, s)
    return dashboard


def get_latest_dashboard(
    app_settings: Settings | None = None,
) -> ThesisDashboard | None:
    doc = load_raw(app_settings)
    dashboards = doc.get("dashboards") or []
    if not dashboards:
        return None
    try:
        return ThesisDashboard.model_validate(dashboards[0])
    except Exception as exc:  # noqa: BLE001
        logger.warning("thesis_latest_invalid err=%s", exc)
        return None


def get_snapshots(
    ticker: str,
    *,
    app_settings: Settings | None = None,
) -> list[ThesisSnapshot]:
    """Newest-first snapshot ring for one ticker."""
    key = ticker.upper()
    doc = load_raw(app_settings)
    raw_list = (doc.get("snapshots") or {}).get(key) or []
    out: list[ThesisSnapshot] = []
    for item in raw_list:
        try:
            out.append(ThesisSnapshot.model_validate(item))
        except Exception as exc:  # noqa: BLE001
            logger.warning("thesis_snapshot_invalid ticker=%s err=%s", key, exc)
    return out


def get_latest_snapshot(
    ticker: str,
    *,
    app_settings: Settings | None = None,
) -> ThesisSnapshot | None:
    snaps = get_snapshots(ticker, app_settings=app_settings)
    return snaps[0] if snaps else None


def append_snapshot(
    snapshot: ThesisSnapshot,
    *,
    app_settings: Settings | None = None,
    ring_size: int | None = None,
) -> ThesisSnapshot:
    """Prepend snapshot into per-ticker ring (newest first)."""
    s = app_settings if app_settings is not None else default_settings
    n = (
        ring_size
        if ring_size is not None
        else int(getattr(s, "thesis_snapshot_ring_size", 8))
    )
    key = snapshot.ticker.upper()
    payload = snapshot.model_dump(mode="json")
    with _LOCK:
        doc = load_raw(s)
        snaps = dict(doc.get("snapshots") or {})
        ring = [payload] + list(snaps.get(key) or [])
        snaps[key] = ring[: max(1, n)]
        doc["snapshots"] = snaps
        save_raw(doc, s)
    return snapshot
