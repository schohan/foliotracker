"""Flexible ticker intake — extract, validate, membership-idempotent bulk add.

Channels (CSV / paste / OCR text / speech transcript) share this parser.
Never invents tickers; never moves existing Held/Watched membership on duplicate.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Callable, Literal

from app.configs.settings import Settings, settings as default_settings
from app.schemas.ticker import InvalidTickerError, normalize_ticker
from app.schemas.watchlist import ListKind, WatchlistMembership
from app.services import watchlist_store as store

logger = logging.getLogger(__name__)

QuoteStatus = Literal["ok", "not_found", "unknown"]
QuoteChecker = Callable[[str], QuoteStatus]
LlmCaller = Callable[[str], str]

# Token-ish candidates (letters + optional .suffix). Digits rejected by normalize.
_TOKEN_RE = re.compile(r"[A-Za-z]{1,10}(?:\.[A-Za-z]{1,3})?")

# Broker/OCR quote row: leading ALL-CAPS ticker, optional short OCR junk, then a price.
_OCR_TICKER_PRICE_LINE_RE = re.compile(
    r"^\s*([A-Z]{1,5}(?:\.[A-Z]{1,3})?)"
    r"(?:\s*(?:[|\\/\-]+|[A-Za-z]{1,3})){0,3}"
    r"\s*"
    r"(\d{1,7}(?:\.\d{1,4})?)\b"
)

_PRICE_RE = re.compile(r"\b\d{1,7}\.\d{2,4}\b")
_PCT_CHANGE_RE = re.compile(r"\(\s*[+-]?\d+(?:\.\d+)?%\s*\)")

# Headers / UI chrome / company-name OCR debris — never invent from these.
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
        # Spoken/OCR company names & legal suffixes
        "APPLE",
        "GOOGLE",
        "MICROSOFT",
        "AMAZON",
        "NVIDIA",
        "TESLA",
        "ALPHABET",
        "APPLIED",
        "MATERIALS",
        "ADVANCED",
        "MICRO",
        "DEVICES",
        "SPACE",
        "EXPLORATION",
        "DIGITAL",
        "TECH",
        "TECHNOLOGY",
        "TECHNOLOG",
        "HOLDINGS",
        "HOLDIN",
        "CORP",
        "CORPOR",
        "INC",
        "LTD",
        "LLC",
        "PLC",
        "GROUP",
        "CLASS",
        "COMMON",
        "PREFERRED",
        "REEL",
        "HYNIX",
        "AMPHENOL",
        "COHERENT",
        "CREDO",
        "LUMENTUM",
        "MARVELL",
    }
)

_LIST_KIND_HEADERS = frozenset({"LIST", "LIST_KIND", "KIND", "TYPE", "STATUS", "BUCKET"})
_TICKER_HEADERS = frozenset(
    {"TICKER", "TICKERS", "SYMBOL", "SYMBOLS", "SYM", "CODE", "SECURITY"}
)

_QUOTE_WORKERS = 6


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


def looks_like_ocr_portfolio(text: str) -> bool:
    """Detect broker-screenshot OCR: many price lines and/or % changes."""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if len(lines) < 3:
        return False
    price_lines = sum(1 for ln in lines if _PRICE_RE.search(ln))
    pct_lines = sum(1 for ln in lines if _PCT_CHANGE_RE.search(ln))
    if price_lines >= 3:
        return True
    if price_lines >= 2 and pct_lines >= 2:
        return True
    lowered = text.lower()
    return price_lines >= 2 and ("ticker" in lowered or "portfolio" in lowered)


def _extract_ocr_portfolio(text: str) -> ExtractedTickers:
    """Only leading ALL-CAPS ticker tokens that sit on a quote/price row."""
    out = ExtractedTickers()
    seen_valid: set[str] = set()
    seen_reject: set[str] = set()
    for line in text.splitlines():
        match = _OCR_TICKER_PRICE_LINE_RE.match(line)
        if not match:
            continue
        token = match.group(1)
        if not _add_valid(out, seen_valid, token):
            _record_reject(out, token, seen_reject)
    return out


def _default_llm_caller(prompt: str) -> str:
    from google import genai

    if not default_settings.google_api_key:
        raise RuntimeError("GOOGLE_API_KEY is not set")
    client = genai.Client(api_key=default_settings.google_api_key)
    interaction = client.interactions.create(
        model=default_settings.default_model,
        input=prompt,
    )
    # Prefer top-level text; fall back to steps like thesis_agent.
    text = getattr(interaction, "text", None)
    if isinstance(text, str) and text.strip():
        return text
    chunks: list[str] = []
    for step in getattr(interaction, "steps", None) or []:
        content = getattr(step, "content", None) or []
        if isinstance(step, dict):
            content = step.get("content") or []
        for part in content:
            part_text = getattr(part, "text", None)
            if part_text is None and isinstance(part, dict):
                part_text = part.get("text")
            if part_text:
                chunks.append(str(part_text))
    return "".join(chunks)


def _parse_llm_ticker_list(raw: str) -> list[str]:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\[[\s\S]*\]", text)
        if not match:
            return []
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            return []
    if not isinstance(data, list):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for item in data:
        if not isinstance(item, str):
            continue
        norm = _try_normalize(item)
        if norm is None or norm in seen:
            continue
        seen.add(norm)
        out.append(norm)
    return out


def extract_tickers_via_llm(
    text: str,
    *,
    llm_caller: LlmCaller | None = None,
) -> list[str]:
    """Ask the model for ticker symbols only (OCR fallback)."""
    prompt = (
        "Extract stock ticker symbols from the following OCR / portfolio text.\n"
        "Return ONLY a JSON array of uppercase ticker strings, e.g. "
        '["AMAT","AMD","MRVL"].\n'
        "Rules:\n"
        "- Include only real exchange ticker symbols (usually 1–5 letters).\n"
        "- Do NOT include company names, prices, percentages, OCR junk, "
        "or common words.\n"
        "- If unsure whether a token is a ticker, omit it.\n"
        "- No markdown, no commentary.\n\n"
        f"TEXT:\n{text[:8000]}"
    )
    caller = llm_caller or _default_llm_caller
    try:
        raw = caller(prompt)
    except Exception as exc:  # noqa: BLE001
        logger.warning("ticker_intake_llm_failed err=%s", exc)
        return []
    return _parse_llm_ticker_list(raw)


def extract_tickers_from_text(
    text: str,
    *,
    llm_caller: LlmCaller | None = None,
    allow_llm: bool = True,
) -> ExtractedTickers:
    """Parse CSV / free text / OCR / transcript into candidate tickers."""
    out = ExtractedTickers()
    if text is None:
        return out
    raw = text.strip()
    if not raw:
        return out

    seen_valid: set[str] = set()
    seen_reject: set[str] = set()

    if looks_like_ocr_portfolio(raw):
        ocr = _extract_ocr_portfolio(raw)
        if ocr.tickers:
            return ocr
        if allow_llm and (
            llm_caller is not None or default_settings.google_api_key
        ):
            seen_llm = set(ocr.tickers)
            for ticker in extract_tickers_via_llm(raw, llm_caller=llm_caller):
                _add_valid(ocr, seen_llm, ticker)
            if ocr.tickers:
                logger.info(
                    "ticker_intake_llm_ocr count=%s",
                    len(ocr.tickers),
                )
                return ocr
        return ocr

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
            tokens = [m.group(0) for m in _TOKEN_RE.finditer(segment)]
            if not tokens:
                continue
            # Whole segment is a single short ticker (e.g. "nvda").
            if len(tokens) == 1 and _TOKEN_RE.fullmatch(segment.strip()):
                if not _add_valid(out, seen_valid, tokens[0]):
                    _record_reject(out, tokens[0], seen_reject)
                continue
            # Pure ticker paste ("BRK.B meta") may be lowercase. Longer
            # Title-Case company words are not all short → ALL-CAPS only.
            pure_paste = all(len(t) <= 5 or "." in t for t in tokens)
            for token in tokens:
                if not pure_paste and token != token.upper():
                    _record_reject(out, token, seen_reject)
                    continue
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


def _default_quote_checker(ticker: str) -> QuoteStatus:
    from app.tools.finance.yahoo_finance import ticker_exists

    try:
        exists = ticker_exists(ticker)
    except InvalidTickerError:
        return "not_found"
    if exists is True:
        return "ok"
    if exists is False:
        return "not_found"
    return "unknown"


def filter_tickers_by_quote(
    tickers: list[str],
    *,
    quote_checker: QuoteChecker | None = None,
) -> tuple[list[str], list[str]]:
    """Validate candidates against a quote service.

    Returns (accepted, rejected_not_found). Upstream/timeout → accept
    (fail open) so paste still works when Yahoo is flaky.
    """
    if not tickers:
        return [], []
    checker = quote_checker or _default_quote_checker
    accepted: list[str] = []
    rejected: list[str] = []
    # Preserve input order while checking in parallel.
    status_by_ticker: dict[str, QuoteStatus] = {}
    workers = min(_QUOTE_WORKERS, len(tickers))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(checker, t): t for t in tickers}
        for fut in as_completed(futures):
            t = futures[fut]
            try:
                status_by_ticker[t] = fut.result()
            except Exception:  # noqa: BLE001
                status_by_ticker[t] = "unknown"
    for t in tickers:
        status = status_by_ticker.get(t, "unknown")
        if status == "not_found":
            rejected.append(t)
        else:
            accepted.append(t)
    return accepted, rejected


def apply_intake(
    text: str,
    list_kind: ListKind,
    *,
    app_settings: Settings | None = None,
    quote_checker: QuoteChecker | None = None,
    llm_caller: LlmCaller | None = None,
    validate_quotes: bool = True,
) -> IntakeResult:
    """Extract tickers and add only those absent from Held ∪ Watched.

    Membership-first: no research. Duplicates ignored (no list move).
    Candidates are quote-validated before add (reject clear unknowns).
    """
    s = app_settings if app_settings is not None else default_settings
    extracted = extract_tickers_from_text(
        text,
        llm_caller=llm_caller,
    )
    candidates = list(extracted.tickers)
    rejected = list(extracted.rejected_invalid)

    if validate_quotes and candidates:
        accepted, quote_rejected = filter_tickers_by_quote(
            candidates,
            quote_checker=quote_checker,
        )
        rejected.extend(quote_rejected)
        candidates = accepted

    if not candidates and not rejected:
        return IntakeResult(
            added=[],
            skipped_duplicate=[],
            rejected_invalid=[],
            membership=store.get_membership(s),
            error_message="No tickers found. Paste symbols, upload a CSV, or try again.",
        )
    if not candidates:
        return IntakeResult(
            added=[],
            skipped_duplicate=[],
            rejected_invalid=rejected,
            membership=store.get_membership(s),
            error_message="No valid tickers found.",
        )

    membership = store.get_membership(s)
    existing = set(membership.held) | set(membership.watched)
    added: list[str] = []
    skipped: list[str] = []

    held = list(membership.held)
    watched = list(membership.watched)

    for t in candidates:
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
            len(rejected),
        )
    else:
        membership = store.get_membership(s)

    return IntakeResult(
        added=added,
        skipped_duplicate=skipped,
        rejected_invalid=rejected,
        membership=membership,
        error_message=None,
    )
