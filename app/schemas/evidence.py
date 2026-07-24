"""Evidence layer — structured, citable outputs for every research step."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class BundleStatus(str, Enum):
    OK = "ok"
    PARTIAL = "partial"
    ERROR = "error"


class Evidence(BaseModel):
    """Atomic research finding consumed by aggregators and thesis agents."""

    id: str = Field(description="Stable evidence id for thesis citations")
    type: str = Field(description="Evidence category, e.g. financial, news, sec")
    source: str = Field(description="Human-readable source name")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score")
    timestamp: datetime = Field(default_factory=datetime.now)
    citation: str | None = Field(default=None, description="URL or document reference")
    data: dict[str, Any] = Field(default_factory=dict)


class EvidenceConflict(BaseModel):
    """Deterministic disagreement between evidence items (no LLM)."""

    id: str
    topic: str = Field(description="Conflict topic, e.g. growth, margin, headline_tone")
    item_ids: list[str] = Field(description="Disagreeing evidence ids")
    summary: str = Field(description="Short deterministic description")
    severity: Literal["info", "warn"] = "warn"


class EvidenceBundle(BaseModel):
    """Collection of evidence for a single ticker or research session."""

    ticker: str
    items: list[Evidence] = Field(default_factory=list)
    conflicts: list[EvidenceConflict] = Field(default_factory=list)
    status: BundleStatus = BundleStatus.OK
