"""Local persistence for ThesisDashboard ring (brief_store pattern)."""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any

from app.configs.settings import Settings, settings as default_settings
from app.schemas.thesis import ThesisDashboard

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()


def _store_path(app_settings: Settings | None = None) -> Path:
    s = app_settings if app_settings is not None else default_settings
    return Path(s.thesis_store_path)


def _default_doc() -> dict[str, Any]:
    return {"dashboards": []}


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
            return _default_doc()
        return {"dashboards": dashboards}
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        logger.warning("thesis_store_corrupt path=%s err=%s", path, exc)
        return _default_doc()


def save_raw(doc: dict[str, Any], app_settings: Settings | None = None) -> None:
    path = _store_path(app_settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(doc, indent=2, default=str) + "\n", encoding="utf-8")
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
