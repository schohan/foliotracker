"""Flexible ticker intake — extract, validate, membership-idempotent bulk add.

Channels (CSV / paste / OCR text / speech transcript) share this parser.
Never invents tickers; never moves existing Held/Watched membership on duplicate.
"""

from __future__ import annotations

import csv
import io
import logging
import re
from dataclasses import dataclass, field

from app.configs.settings import Settings, settings as default_settings
from app.schemas.ticker import InvalidTickerError, normalize_ticker
from app.schemas.watchlist import ListKind, WatchlistMembership
from app.services import watchlist_store as store

logger = logging.getLogger(__name__)

# Token-ish candidates (letters + optional .suffix). Digits rejected by normalize.
_TOKEN_RE = re.compile(r"[A-Za-z]{1,10}(?:\.[A-Za-z]{1,3})?")

# Headers / UI chrome — never invent from these.
_BLOCKLIST = frozenset(
    {
        "THE",
        "AND",
        "FOR",
        "ARE",
        "BUT",
        "NOT",
        "YOU",
        "ALL",
        "CAN",
        "HAD",
        "HER",
        "WAS",
        "ONE",
        "OUR",
        "OUT",
        "DAY",
        "GET",
        "HAS",
        "HIM",
        "HIS",
        "HOW",
        "DID",
        "ITS",
        "LET",
        "PUT",
        "SAY",
        "SHE",
        "TOO",
        "USE",
        "FROM",
        "WITH",
        "THIS",
        "THAT",
        "HAVE",
        "WILL",
        "YOUR",
        "WHAT",
        "WHEN",
        "THAN",
        "THEM",
        "THEN",
        "SOME",
        "INTO",
        "ALSO",
        "JUST",
        "ONLY",
        "STOCK",
        "STOCKS",
        "SHARES",
        "SHARE",
        "PRICE",
        "PRICES",
        "MARKET",
        "MARKETS",
        "HELD",
        "WATCHED",
        "WATCHLIST",
        "TICKER",
        "TICKERS",
        "SYMBOL",
        "SYMBOLS",
        "COMPANY",
        "NAME",
        "NAMES",
        "LIST",
        "KIND",
        "TYPE",
        "PORTFOLIO",
        "BUY",
        "SELL",
        "HOLD",
        "TRIM",
        "ADD",
        "TRUE",
        "FALSE",
        "NULL",
        "NONE",
        "YES",
        "NO",
        "DATE",
        "TIME",
        "TODAY",
        "AMOUNT",
        "VALUE",
        "TOTAL",
        "WEIGHT",
        "SECTOR",
        "INDUSTRY",
        "USD",
        "CAD",
        "EUR",
        "GBP",
        "HTTP",
        "HTTPS",
        "WWW",
        "COM",
        "ORG",
        "NET",
        "A",
        "I",
        "AN",
        "AS",
        "AT",
        "BE",
        "BY",
        "DO",
        "GO",
        "IF",
        "IN",
        "IS",
        "IT",
        "ME",
        "MY",
        "OF",
        "ON",
        "OR",
        "SO",
        "TO",
        "UP",
        "US",
        "WE",
        "AM",
        "PM",
        "VS",
        "OK",
        "HELLO",
        "WORLD",
        "PLEASE",
        "THANKS",
        "THANK",
        # Spoken/OCR company names (tickers are AAPL/MSFT/…)
        "APPLE",
        "GOOGLE",
        "MICROSOFT",
        "AMAZON",
        "NVIDIA",
        "TESLA",
        "ALPHABET",
    }
)

_LIST_KIND_HEADERS = frozenset({"LIST", "LIST_KIND", "KIND", "TYPE", "STATUS", "BUCKET"})
_TICKER_HEADERS = frozenset(
    {"TICKER", "TICKERS", "SYMBOL", "SYMBOLS", "SYM", "CODE", "SECURITY"}
)


@dataclass
class ExtractedTickers:
    """Ordered unique valid tickers + rejected raw tokens."""

    tickers: list[str] = field(default_factory=list)
    rejected_invalid: list[str] = field(default_factory=list)
    list_kinds: dict[str, ListKind] = field(default_factory=dict)


@dataclass
class IntakeResult:
    added: list[str]
    skipped_duplicate: list[str]
    rejected_invalid: list[str]
    membership: WatchlistMembership
    error_message: str | None = None


def _try_normalize(raw: str) -> str | None:
    token = raw.strip().strip("\"'").upper()
    if not token or token in _BLOCKLIST:
        return None
    if len(token) < 2 and "." not in token:
        return None
    try:
        return normalize_ticker(token)
    except InvalidTickerError:
        return None


def _record_reject(
    out: ExtractedTickers,
    raw: str,
    seen_reject: set[str],
    *,
    force: bool = False,
) -> None:
    cleaned = raw.strip().strip("\"'")
    if not cleaned:
        return
    key = cleaned.upper()
    if key in _BLOCKLIST or key in seen_reject:
        return
    if not force and not _TOKEN_RE.fullmatch(cleaned) and not _TOKEN_RE.fullmatch(key):
        return
    seen_reject.add(key)
    out.rejected_invalid.append(cleaned)


def _add_valid(
    out: ExtractedTickers,
    seen_valid: set[str],
    token: str,
    *,
    kind: ListKind | None = None,
) -> bool:
    norm = _try_normalize(token)
    if norm is None:
        return False
    if norm not in seen_valid:
        seen_valid.add(norm)
        out.tickers.append(norm)
    if kind is not None:
        out.list_kinds[norm] = kind
    return True


def _is_list_like(text: str) -> bool:
    """True when input looks like a ticker list, not prose."""
    tokens = _TOKEN_RE.findall(text)
    if not tokens:
        return False
    # Delimiters strongly indicate a list.
    if any(d in text for d in ",;\n\t|/"):
        return True
    short = sum(1 for t in tokens if len(t) <= 5 or "." in t)
    return short == len(tokens) and len(tokens) <= 80


def extract_tickers_from_text(text: str) -> ExtractedTickers:
    """Parse CSV / free text / OCR / transcript into candidate tickers."""
    out = ExtractedTickers()
    if text is None:
        return out
    raw = text.strip()
    if not raw:
        return out

    seen_valid: set[str] = set()
    seen_reject: set[str] = set()

    if "," in raw or "\t" in raw:
        try:
            csv_result = _extract_csv(raw)
            if csv_result.tickers or csv_result.rejected_invalid:
                return csv_result
        except csv.Error:
            pass

    # Delimiter-separated segments (paste / speech chunks).
    segments = [s.strip() for s in re.split(r"[,;\n\r\t|/]+", raw) if s.strip()]
    if len(segments) >= 2 or _is_list_like(raw):
        for segment in segments if len(segments) >= 2 else [raw]:
            for match in _TOKEN_RE.finditer(segment):
                token = match.group(0)
                if not _add_valid(out, seen_valid, token):
                    _record_reject(out, token, seen_reject)
        return out

    # Prose / noisy OCR: only accept ALL-CAPS ticker-shaped tokens (fail closed).
    for match in _TOKEN_RE.finditer(raw):
        token = match.group(0)
        if token != token.upper():
            continue
        if not _add_valid(out, seen_valid, token):
            _record_reject(out, token, seen_reject)
    return out


def _extract_csv(raw: str) -> ExtractedTickers:
    out = ExtractedTickers()
    seen_valid: set[str] = set()
    seen_reject: set[str] = set()
    sample = raw[:2048]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t;")
    except csv.Error:
        dialect = csv.excel
        if "\t" in sample and sample.count("\t") >= sample.count(","):
            dialect = csv.excel_tab
    reader = csv.reader(io.StringIO(raw), dialect)
    rows = [row for row in reader if any(cell.strip() for cell in row)]
    if not rows:
        return out

    header = [c.strip().upper() for c in rows[0]]
    ticker_col: int | None = None
    kind_col: int | None = None
    has_header = False
    for i, h in enumerate(header):
        if h in _TICKER_HEADERS:
            ticker_col = i
            has_header = True
        if h in _LIST_KIND_HEADERS:
            kind_col = i
            has_header = True

    data_rows = rows[1:] if has_header else rows
    if has_header and ticker_col is None:
        ticker_col = 0

    for row in data_rows:
        if not row:
            continue
        cells = [c.strip() for c in row]
        if ticker_col is not None:
            candidates = [cells[ticker_col]] if ticker_col < len(cells) else []
        else:
            candidates = cells

        row_kind: ListKind | None = None
        if kind_col is not None and kind_col < len(cells):
            row_kind = _parse_list_kind(cells[kind_col])

        for cell in candidates:
            if not cell:
                continue
            pieces = re.split(r"[\s;|/]+", cell)
            for piece in pieces:
                if not piece:
                    continue
                if not _add_valid(out, seen_valid, piece, kind=row_kind):
                    _record_reject(out, piece, seen_reject, force=True)
    return out


def _parse_list_kind(raw: str) -> ListKind | None:
    v = raw.strip().lower()
    if v in ("held", "hold", "holding", "holdings", "own", "owned"):
        return ListKind.HELD
    if v in ("watched", "watch", "watchlist", "watching"):
        return ListKind.WATCHED
    return None


def apply_intake(
    text: str,
    list_kind: ListKind,
    *,
    app_settings: Settings | None = None,
) -> IntakeResult:
    """Extract tickers and add only those absent from Held ∪ Watched.

    Membership-first: no research. Duplicates ignored (no list move).
    """
    s = app_settings if app_settings is not None else default_settings
    extracted = extract_tickers_from_text(text)
    if not extracted.tickers and not extracted.rejected_invalid:
        return IntakeResult(
            added=[],
            skipped_duplicate=[],
            rejected_invalid=[],
            membership=store.get_membership(s),
            error_message="No tickers found. Paste symbols, upload a CSV, or try again.",
        )
    if not extracted.tickers:
        return IntakeResult(
            added=[],
            skipped_duplicate=[],
            rejected_invalid=list(extracted.rejected_invalid),
            membership=store.get_membership(s),
            error_message="No valid tickers found.",
        )

    membership = store.get_membership(s)
    existing = set(membership.held) | set(membership.watched)
    added: list[str] = []
    skipped: list[str] = []

    held = list(membership.held)
    watched = list(membership.watched)

    for t in extracted.tickers:
        if t in existing:
            skipped.append(t)
            continue
        kind = extracted.list_kinds.get(t, list_kind)
        if kind == ListKind.HELD:
            held.append(t)
        else:
            watched.append(t)
        existing.add(t)
        added.append(t)

    if added:
        membership = store.put_membership(held, watched, s)
        logger.info(
            "watchlist_intake added=%s skipped=%s rejected=%s",
            len(added),
            len(skipped),
            len(extracted.rejected_invalid),
        )
    else:
        membership = store.get_membership(s)

    return IntakeResult(
        added=added,
        skipped_duplicate=skipped,
        rejected_invalid=list(extracted.rejected_invalid),
        membership=membership,
        error_message=None,
    )
