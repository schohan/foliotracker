"""Evidence builders and aggregator — pure Python, no LLM."""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime, timezone

from app.configs.settings import settings
from app.schemas.evidence import (
    BundleStatus,
    Evidence,
    EvidenceBundle,
    EvidenceConflict,
)
from app.schemas.filings import SecFilingsBatch
from app.schemas.financials import FinancialMetrics
from app.schemas.news import NewsBatch

logger = logging.getLogger(__name__)

YAHOO_SOURCE = "Yahoo Finance"
YAHOO_CONFIDENCE = 0.95
NEWS_SOURCE = "Google News"
NEWS_CONFIDENCE = 0.7
SEC_SOURCE = "SEC EDGAR"
SEC_CONFIDENCE = 0.9
_MATERIAL_EVENT_FORMS = frozenset({"8-K", "8-K/A"})

_POSITIVE_CUES = frozenset(
    {
        "surge",
        "soar",
        "beat",
        "beats",
        "growth",
        "record",
        "rally",
        "upgrade",
        "upgraded",
        "profit",
        "strong",
        "outperform",
        "bullish",
        "gain",
        "gains",
        "rise",
        "rises",
        "jump",
        "jumps",
    }
)
_NEGATIVE_CUES = frozenset(
    {
        "plunge",
        "plunges",
        "miss",
        "misses",
        "cut",
        "cuts",
        "downgrade",
        "downgraded",
        "lawsuit",
        "fraud",
        "decline",
        "weak",
        "loss",
        "losses",
        "crash",
        "fall",
        "falls",
        "drop",
        "drops",
        "bearish",
        "slump",
        "warning",
    }
)


class EmptyMetricsError(ValueError):
    """All numeric metric fields are null/missing."""


class EmptyEvidenceError(ValueError):
    """Aggregator received no evidence items."""


_SCALAR_METRIC_FIELDS = (
    "market_cap",
    "revenue_growth",
    "gross_margin",
    "operating_margin",
    "free_cash_flow",
    "debt_to_equity",
    "pe_ratio",
    "trailing_pe",
    "forward_pe",
    "eps_trailing",
    "eps_forward",
    "earnings_growth",
    "return_on_equity",
    "current_ratio",
    "total_cash",
    "total_debt",
)


def _metric_fields(metrics: FinancialMetrics) -> dict:
    """Serialize metrics for evidence.data (include 2C.2 enrichment)."""
    return metrics.model_dump(mode="json", exclude_none=True)


def _has_any_metric(metrics: FinancialMetrics) -> bool:
    if any(getattr(metrics, field) is not None for field in _SCALAR_METRIC_FIELDS):
        return True
    if metrics.revenue_history or metrics.earnings_history:
        return True
    if metrics.balance_sheet is not None or metrics.cash_flow is not None:
        return True
    if metrics.returns is not None:
        r = metrics.returns
        if r.return_3m is not None or r.return_1y is not None or r.return_ytd is not None:
            return True
    return False


def evidence_id_for(ticker: str, data: dict) -> str:
    digest = hashlib.sha256(
        repr(sorted((k, v) for k, v in data.items())).encode("utf-8")
    ).hexdigest()[:10]
    return f"ev_financial_{ticker}_{digest}"


def news_evidence_id_for(ticker: str, data: dict) -> str:
    digest = hashlib.sha256(
        repr(sorted((k, v) for k, v in data.items())).encode("utf-8")
    ).hexdigest()[:10]
    return f"ev_news_{ticker}_{digest}"


def sec_evidence_id_for(ticker: str, data: dict) -> str:
    digest = hashlib.sha256(
        repr(sorted((k, v) for k, v in data.items())).encode("utf-8")
    ).hexdigest()[:10]
    return f"ev_sec_{ticker}_{digest}"


def evidence_from_metrics(metrics: FinancialMetrics) -> Evidence:
    """Convert FinancialMetrics into a single financial Evidence item."""
    if not _has_any_metric(metrics):
        raise EmptyMetricsError(f"no numeric metrics for {metrics.ticker}")

    data = _metric_fields(metrics)
    eid = evidence_id_for(metrics.ticker, data)
    source_id = (metrics.source_id or "yahoo").lower()
    if source_id == "sec_xbrl":
        source_name = "SEC XBRL"
        citation = f"https://data.sec.gov/api/xbrl/companyfacts/"
        confidence = 0.95
    elif source_id == "merged":
        source_name = "Merged fundamentals"
        citation = f"https://finance.yahoo.com/quote/{metrics.ticker}"
        confidence = YAHOO_CONFIDENCE
    else:
        source_name = YAHOO_SOURCE
        citation = f"https://finance.yahoo.com/quote/{metrics.ticker}"
        confidence = YAHOO_CONFIDENCE
    if metrics.field_provenance:
        data = {
            **data,
            "field_provenance": {
                k: v.model_dump(mode="json")
                for k, v in metrics.field_provenance.items()
            },
        }
    return Evidence(
        id=eid,
        type="financial",
        source=source_name,
        confidence=confidence,
        timestamp=datetime.now(timezone.utc),
        citation=citation,
        data=data,
    )


def evidence_from_news(batch: NewsBatch) -> list[Evidence]:
    """Convert a NewsBatch into news Evidence items (one per article)."""
    items: list[Evidence] = []
    for article in batch.articles:
        published = article.published_at
        published_iso = published.isoformat() if published is not None else None
        data = {
            "ticker": batch.ticker,
            "title": article.title,
            "publisher": article.publisher,
            "published_at": published_iso,
            "url": article.url,
        }
        eid = news_evidence_id_for(batch.ticker, data)
        items.append(
            Evidence(
                id=eid,
                type="news",
                source=NEWS_SOURCE,
                confidence=NEWS_CONFIDENCE,
                timestamp=datetime.now(timezone.utc),
                citation=article.url,
                data=data,
            )
        )
    return items


def evidence_from_filings(batch: SecFilingsBatch) -> list[Evidence]:
    """Convert SecFilingsBatch into sec Evidence items (one per filing)."""
    items: list[Evidence] = []
    for filing in batch.filings:
        filing_date = (
            filing.filing_date.isoformat() if filing.filing_date is not None else None
        )
        report_date = (
            filing.report_date.isoformat() if filing.report_date is not None else None
        )
        title = f"{filing.form} filed {filing_date or 'unknown date'}"
        data = {
            "ticker": batch.ticker,
            "cik": batch.cik,
            "company_name": batch.company_name,
            "form": filing.form,
            "filing_date": filing_date,
            "report_date": report_date,
            "accession_number": filing.accession_number,
            "primary_document": filing.primary_document,
            "title": title,
            "url": filing.url,
        }
        eid = sec_evidence_id_for(batch.ticker, data)
        items.append(
            Evidence(
                id=eid,
                type="sec",
                source=SEC_SOURCE,
                confidence=SEC_CONFIDENCE,
                timestamp=datetime.now(timezone.utc),
                citation=filing.url,
                data=data,
            )
        )
    return items


def _normalize_title(title: str) -> str:
    return re.sub(r"\s+", " ", title.strip().lower())


def _headline_tone(title: str) -> str | None:
    """Return 'positive', 'negative', or None from simple keyword cues."""
    tokens = set(re.findall(r"[a-z]+", title.lower()))
    pos = bool(tokens & _POSITIVE_CUES)
    neg = bool(tokens & _NEGATIVE_CUES)
    if pos and not neg:
        return "positive"
    if neg and not pos:
        return "negative"
    return None


# Core Phase 0 scalars — nulls here mark financial evidence as partial.
# Optional 2C.2 enrichment (forward_pe, returns, statements) may be null.
_CORE_FINANCIAL_KEYS = (
    "market_cap",
    "revenue_growth",
    "gross_margin",
    "operating_margin",
    "free_cash_flow",
    "debt_to_equity",
    "pe_ratio",
)


def _financial_partial(item: Evidence) -> bool:
    values = [item.data.get(k) for k in _CORE_FINANCIAL_KEYS]
    if not any(v is not None for v in values):
        return True
    return any(v is None for v in values)


def _dedupe_items(items: list[Evidence]) -> list[Evidence]:
    """Dedupe by (type, citation) or (type, normalized title); keep best."""

    def score(ev: Evidence) -> tuple[float, float]:
        ts = ev.timestamp.timestamp() if ev.timestamp else 0.0
        return (ev.confidence, ts)

    def matches(a: Evidence, b: Evidence) -> bool:
        if a.type != b.type:
            return False
        if (
            a.citation
            and b.citation
            and a.citation.strip().lower() == b.citation.strip().lower()
        ):
            return True
        title_a = a.data.get("title")
        title_b = b.data.get("title")
        if isinstance(title_a, str) and isinstance(title_b, str):
            return _normalize_title(title_a) == _normalize_title(title_b)
        return False

    winners: list[Evidence] = []
    for item in items:
        idx = next((i for i, w in enumerate(winners) if matches(w, item)), None)
        if idx is None:
            winners.append(item)
        elif score(item) > score(winners[idx]):
            winners[idx] = item
    return winners


def _cap_news(items: list[Evidence], max_articles: int) -> list[Evidence]:
    financial = [i for i in items if i.type == "financial"]
    news = [i for i in items if i.type == "news"]
    other = [i for i in items if i.type not in ("financial", "news")]

    def published_key(ev: Evidence) -> float:
        raw = ev.data.get("published_at")
        if isinstance(raw, str):
            try:
                return datetime.fromisoformat(raw).timestamp()
            except ValueError:
                pass
        return ev.timestamp.timestamp() if ev.timestamp else 0.0

    news_sorted = sorted(news, key=published_key, reverse=True)[:max_articles]
    return financial + news_sorted + other


def _cap_sec(items: list[Evidence], max_filings: int) -> list[Evidence]:
    sec = [i for i in items if i.type == "sec"]
    other = [i for i in items if i.type != "sec"]

    def filing_key(ev: Evidence) -> float:
        raw = ev.data.get("filing_date")
        if isinstance(raw, str):
            try:
                return datetime.fromisoformat(raw).timestamp()
            except ValueError:
                pass
        return ev.timestamp.timestamp() if ev.timestamp else 0.0

    sec_sorted = sorted(sec, key=filing_key, reverse=True)[:max_filings]
    return other + sec_sorted


def _detect_conflicts(items: list[Evidence]) -> list[EvidenceConflict]:
    conflicts: list[EvidenceConflict] = []
    news = [i for i in items if i.type == "news"]
    financial = [i for i in items if i.type == "financial"]
    sec = [i for i in items if i.type == "sec"]

    # News vs news opposing headline tones
    pos_news = [i for i in news if _headline_tone(str(i.data.get("title") or "")) == "positive"]
    neg_news = [i for i in news if _headline_tone(str(i.data.get("title") or "")) == "negative"]
    if pos_news and neg_news:
        ids = [pos_news[0].id, neg_news[0].id]
        digest = hashlib.sha256("|".join(sorted(ids)).encode()).hexdigest()[:8]
        conflicts.append(
            EvidenceConflict(
                id=f"conflict_headline_tone_{digest}",
                topic="headline_tone",
                item_ids=ids,
                summary=(
                    "News headlines disagree on tone: positive vs negative cues "
                    "in recent coverage."
                ),
                severity="warn",
            )
        )

    # News tone vs financial growth / margin signals
    if financial and news:
        fin = financial[0]
        growth = fin.data.get("revenue_growth")
        gross = fin.data.get("gross_margin")
        fin_positive = (isinstance(growth, (int, float)) and growth > 0) or (
            isinstance(gross, (int, float)) and gross > 0.4
        )
        fin_negative = isinstance(growth, (int, float)) and growth < 0

        if fin_positive and neg_news:
            ids = [fin.id, neg_news[0].id]
            digest = hashlib.sha256("|".join(sorted(ids)).encode()).hexdigest()[:8]
            conflicts.append(
                EvidenceConflict(
                    id=f"conflict_growth_{digest}",
                    topic="growth",
                    item_ids=ids,
                    summary=(
                        "Financial metrics look constructive while recent news "
                        "headlines carry negative cues."
                    ),
                    severity="warn",
                )
            )
        if fin_negative and pos_news:
            ids = [fin.id, pos_news[0].id]
            digest = hashlib.sha256("|".join(sorted(ids)).encode()).hexdigest()[:8]
            conflicts.append(
                EvidenceConflict(
                    id=f"conflict_growth_{digest}",
                    topic="growth",
                    item_ids=ids,
                    summary=(
                        "Financial growth is negative while recent news headlines "
                        "carry positive cues."
                    ),
                    severity="warn",
                )
            )

        if isinstance(gross, (int, float)) and gross < 0.2 and pos_news:
            ids = [fin.id, pos_news[0].id]
            digest = hashlib.sha256("|".join(sorted(ids)).encode()).hexdigest()[:8]
            conflicts.append(
                EvidenceConflict(
                    id=f"conflict_margin_{digest}",
                    topic="margin",
                    item_ids=ids,
                    summary=(
                        "Gross margin is weak while news headlines carry "
                        "positive cues."
                    ),
                    severity="info",
                )
            )

    # Recent 8-K material event vs upbeat headlines
    material_sec = [
        i for i in sec if str(i.data.get("form") or "") in _MATERIAL_EVENT_FORMS
    ]
    if material_sec and pos_news:
        ids = [material_sec[0].id, pos_news[0].id]
        digest = hashlib.sha256("|".join(sorted(ids)).encode()).hexdigest()[:8]
        conflicts.append(
            EvidenceConflict(
                id=f"conflict_material_event_{digest}",
                topic="material_event",
                item_ids=ids,
                summary=(
                    "A recent 8-K material-event filing is present while news "
                    "headlines carry positive cues — verify the event before "
                    "treating coverage as confirmatory."
                ),
                severity="info",
            )
        )

    return conflicts


def aggregate_evidence(
    ticker: str,
    items: list[Evidence],
    *,
    news_failed: bool = False,
    sec_failed: bool = False,
    max_news_articles: int | None = None,
    max_sec_filings: int | None = None,
) -> EvidenceBundle:
    """Merge evidence: dedupe, cap news/SEC, detect conflicts, assign status."""
    if not items and not news_failed and not sec_failed:
        raise EmptyEvidenceError(f"no evidence for {ticker}")
    if not items:
        raise EmptyEvidenceError(f"no evidence for {ticker}")

    max_n = (
        max_news_articles
        if max_news_articles is not None
        else settings.news_max_articles
    )
    max_sec = (
        max_sec_filings
        if max_sec_filings is not None
        else settings.sec_max_filings
    )

    merged = _dedupe_items(list(items))
    merged = _cap_news(merged, max_n)
    merged = _cap_sec(merged, max_sec)
    conflicts = _detect_conflicts(merged)

    financial_items = [i for i in merged if i.type == "financial"]
    news_items = [i for i in merged if i.type == "news"]
    sec_items = [i for i in merged if i.type == "sec"]
    partial = False
    if any(_financial_partial(i) for i in financial_items):
        partial = True
    if news_failed or not news_items:
        # Multi-source spine expects news; missing/failed news → partial
        partial = True
    if sec_failed or not sec_items:
        # Thin Phase 2 expects SEC filings; missing/failed SEC → partial
        partial = True
    if conflicts:
        partial = True

    status = BundleStatus.PARTIAL if partial else BundleStatus.OK
    logger.info(
        "aggregate_ok ticker=%s items=%s conflicts=%s status=%s "
        "news_failed=%s sec_failed=%s",
        ticker,
        len(merged),
        len(conflicts),
        status.value,
        news_failed,
        sec_failed,
    )
    return EvidenceBundle(
        ticker=ticker,
        items=merged,
        conflicts=conflicts,
        status=status,
    )
