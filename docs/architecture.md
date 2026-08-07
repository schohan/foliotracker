# FolioTracker Architecture

**Portfolio Intelligence** — an AI Investment Operating System on [Google ADK](https://adk.dev/). Six AI engines compose over one shared **evidence spine** (fetch → evidence → cite → score); see [Platform shape](#platform-shape--six-engines-one-evidence-spine) below and [PRD §1](PRD.md).

**Status:** Thin Phase 2 + **2C done**. Watchlist + Risk v2 **shipped**. **Daily Decision Brief Slice 1 + triage dashboard shipped** (Engine 1 surface — preserved unchanged). **Flexible ticker intake shipped.** **Portfolio Intelligence vision adopted — Thesis page (Engines 2–6) planned.** **Next:** Brief dogfood Assignment, then Thesis T1. See [TODOS.md](../TODOS.md).

**Related:** [PRD.md](PRD.md) · [implementation-status.md](implementation-status.md) · [TODOS.md](../TODOS.md)

---

## Design principles (non-negotiable)

1. **Agents reason; tools fetch; services calculate.** Agents must not perform HTTP or arithmetic.
2. **Schemas are the contracts.** No free-form agent output as the system of record.
3. **Evidence over vibes.** Downstream agents consume `Evidence`, not raw prose from upstream agents.
4. **Eval-first.** Tests and evals are written and reviewed before implementation code for each phase.
5. **Partial failure is visible.** Missing data yields a degraded, labeled result — never a silent fake thesis.
6. **Frameworks are lenses, not verdicts.** Each investment framework (Graham, Buffett, Lynch, …) is a deterministic service contributing evidence; no single philosophy dictates a rating.
7. **Directive guidance is earned, scoped, and explained.** Buy / hold / trim / research phrasing is allowed **only** from the AI Portfolio Advisor (Engine 6), always with reasoning, confidence, provider label, and the fixed disclaimer. Every other surface stays non-directive.

---

## Platform shape — six engines, one evidence spine

Portfolio Intelligence is six AI engines composing over the same evidence spine ([PRD §1.2](PRD.md)). The spine — sources → per-source cache → merged fundamentals → evidence builders → aggregator → deterministic services → sole-LLM reasoning steps — is what Phases 0–2C built; engines are composition over it, not parallel stacks.

| Engine | Answers | System components | Surface | Status |
|--------|---------|-------------------|---------|--------|
| 1. Market Intelligence | "What changed that matters?" | `brief_classify`, `yahoo_history`, `brief_service`, `brief_insight`, `brief_store`, `/api/brief*` | **Brief page — shipped, preserved unchanged** (E1 enrichment additive, after T3) | **Shipped** |
| 2. Fundamental Engine | Stronger or weaker? | Merged fundamentals (Yahoo + SEC XBRL) → metric services incl. Altman Z / Piotroski F / Beneish M where computable | Thesis page | Planned (T1+) |
| 3. Valuation Engine | Am I paying too much? | Valuation service (Graham / Buffett / Modern sets → six-value ladder) + net asset service | Thesis page | Planned (T2) |
| 4. Investment Framework Engine | How does each philosophy score this? | Framework engine service → `FrameworkScorecard` per philosophy | Thesis page | Planned (T1) |
| 5. Thesis Monitoring | Has my thesis changed? | Thesis snapshot ring store + quarterly diff → closed verdict set | Thesis page | Planned (T3) |
| 6. AI Portfolio Advisor | Buy more / hold / trim / research? | Advisor + explain service (`THESIS_INSIGHT_MODE`, fail-closed) | Thesis page | Planned (T4) |

Shared substrate for every engine: `source_registry` / `source_cache` / `cached_fetch`, `merge_fundamentals` + provenance, evidence builders + aggregator, deterministic scoring services, and the fail-closed insight-provider pattern (`brief_insight` → mirrored by `thesis` advisor). Detailed designs: shipped spine in the Phase 0–2C sections below; Engine 1 in [Daily Decision Brief](#engine-1--daily-decision-brief-shipped); Engines 2–6 in [Portfolio Intelligence — Thesis page](#portfolio-intelligence--thesis-page-engines-26-planned).

---

## Phase 0 — Thin vertical slice (ACTIVE)

### Goal

User provides a ticker → system returns **`EvidenceBundle` + `InvestmentThesis`** where every material claim cites evidence IDs grounded in Yahoo Finance financial metrics.

### In scope

| Piece | Role |
|-------|------|
| `portfolio_research_agent` (root) | Accepts ticker; runs Phase 0 pipeline; returns JSON |
| `yahoo_finance` tool | Fetches metrics; returns structured data (no LLM) |
| `evidence_from_metrics` service | Pure Python: `FinancialMetrics` → `Evidence` (`type=financial`). No LLM. |
| Evidence aggregator (pass-through) | Builds `EvidenceBundle`; assigns stable evidence IDs |
| Local result cache | File-backed cache keyed by ticker; TTL from config; skip pipeline on hit |
| `thesis_agent` | **Only** LLM reasoning step — `InvestmentThesis` with claim→evidence citations |
| Evals + unit tests | Written **before** implementation; human review gate |

`financial_statement_agent` remains a deferred stub (future narrative/interpretation over statements). Phase 0 does **not** use it.

### Phase 1 additions (shipped on Phase 0 spine)

| Piece | Role |
|-------|------|
| `google_news` tool | Google News RSS → `NewsBatch` (no API key; no LLM) |
| `evidence_from_news` service | Pure Python: articles → `Evidence` (`type=news`, confidence 0.7) |
| Evidence aggregator (merge) | Dedupe, news cap, `EvidenceConflict` records; status `partial` on gaps/conflicts |
| Pipeline fan-out | Yahoo + news via thread pool; news failure alone → financial-only `partial` |
| Disagreement surface | `evidence.conflicts` on `Phase0Result` (JSON-first; no custom UI) |

### Phase 2 additions (thin — SEC then scoring)

| Piece | Role | Status |
|-------|------|--------|
| `sec_edgar` tool | EDGAR submissions → `SecFilingsBatch` (metadata only; User-Agent required) | **2A done** |
| `evidence_from_filings` | Pure Python: filings → `Evidence` (`type=sec`, confidence 0.9) | **2A done** |
| Pipeline fan-out | Yahoo + news + SEC; news or SEC failure alone → `partial` | **2A done** |
| Scoring service | Deterministic Growth/Value/Moat/Risk from `FinancialMetrics` → `Scorecard`; no LLM math | **2B done** |

`sec_xbrl` stays stubbed until Phase 2C slice 3. Portfolio/memory/dashboard stay deferred (see TODOS). Thin Phase 2 complete = 2A + 2B.

### Phase 2C — Multi-source ingestion (DONE through 2C.3 — design locked 2026-07-25)

**Job:** Richer, reliable fundamentals for buy / hold / trim / add decisions without a long Yahoo click-tour. Sources are plumbing; field completeness + honest degradation are the product.

**Approach B1 (locked):** Provider port + per-source TTL/quota cache; enrich Yahoo day-1; **SEC XBRL next** for statement truth; Alpha Vantage / FMP later for forward estimates if gaps remain. No Kafka / Celery / medallion warehouse — on-demand fetch + local per-source cache only.

#### Contracts

| Contract | Role |
|----------|------|
| `DataSource` registry | Config-driven: `source_id`, trust/confidence, `ttl_seconds`, soft rate budget (calls/window), timeout, enabled |
| Per-source cache | `.cache/foliotracker/sources/{source_id}/{TICKER}.json` with `fetched_at`, normalized payload, status |
| `FundamentalsSnapshot` | Evolve beyond thin `FinancialMetrics`: profile, returns (YTD/1Y/3M), earnings/revenue series, BS/CF summaries, trailing + forward P/E, FCF; each filled field records `source_id` + `as_of` |
| Merge policy | Fill-nulls by trust ladder; same-field disagreement → conflict + prefer higher trust; never invent values |
| Minimum field set | Editable frozenset `MINIMUM_FUNDAMENTALS_FIELD_PATHS` in `app/schemas/fundamentals_minimum.py` — gate for soften Yahoo-fatal → `partial` |
| Pipeline | Fetch each source independently by TTL; evidence + scoring consume merged snapshot; Yahoo-alone failure → `partial` only if `has_minimum_fundamentals(merged)`, else clear `error` |

#### Target data flow

```
analyze_ticker
        │
        ▼
┌───────────────────────────────┐
│ per-source cache              │  key = ticker × source_id
│ fresh? → reuse                │
│ stale / miss → fetch provider │
└─────────────┬─────────────────┘
              │
    ┌─────────┼─────────┬──────────────┐
    ▼         ▼         ▼              ▼ (later)
 yahoo    google_news  sec_edgar    sec_xbrl / alpha_vantage
    │         │         │              │
    └─────────┴────┬────┘              │
                   ▼                   │
         merge_fundamentals ◄──────────┘
         → FundamentalsSnapshot + provenance
                   │
                   ▼
         evidence builders → aggregator
         score_from_metrics (merged snapshot)
         thesis_agent
                   │
                   ▼
         Phase0Result (+ optional coarser result TTL)
```

#### Implementation slices

| Slice | Deliver | Status |
|-------|---------|--------|
| Docs | This section + PRD/TODOS/implementation-status | **Done** (2026-07-25) |
| 1 | Source registry + per-source cache; wrap existing Yahoo / news / SEC tools; behavior-compatible | **Done** (2026-07-25) |
| 2 | Enrich Yahoo (statements/trends/forward where yfinance allows); expand schemas; evidence + scoring consume richer fields | **Done** (2026-07-25) |
| 3 | Soften Yahoo-fatal once merge rules allow; `sec_xbrl` fundamentals provider | **Done** (2026-07-25) |
| Later | Alpha Vantage OVERVIEW fill-gaps | **Done** (2026-07-25) |
| Next | Portfolio / watchlist dashboard v1 | **Done** (2026-07-25) — FastAPI + `web/` Svelte 5 |

#### Rate limits vs platform

| In scope (2C) | Still out of scope |
|---------------|--------------------|
| Per-source local budgets (calls/window) + skip/defer when exhausted | Redis / multi-tenant rate-limit platform |
| Independent TTL per `source_id` | Background scheduled workers / Kafka |

#### Failure modes (2C additions)

| Codepath | Failure | User sees |
|----------|---------|-----------|
| Per-source cache | Corrupt / IO | Treat as miss; log; fetch |
| Source rate budget exhausted | Soft skip | Serve stale if present, else gap → often `partial` |
| Yahoo down, merge fails min field set | Missing paths in `MINIMUM_FUNDAMENTALS_FIELD_PATHS` | `status=error`, `DATA_FETCH_FAILED` |
| Yahoo down, SEC XBRL (later) fills min set | Enough fundamentals | `status=partial`, provenance shows SEC |
| Field disagreement across providers | Conflict record | Prefer higher trust; `partial` when conflict fires |

### Explicitly NOT in scope (beyond thin Phase 2 / 2C design)

- Technical / social / macro agents
- ADK `ParallelAgent` rewrite (fan-out stays in the Python pipeline)
- Full evidence graph edges / confidence calibration
- Memory layers, Mongo, vector store (local TTL file cache **is** in Phase 0 — see below)
- Position weights / ADK `portfolio_agent` (Risk v2 concentration + correlation shipped; see TODOS)
- Custom HTTP API / UI beyond watchlist + Risk + Brief + intake (Thesis page is the next planned surface; Phase 3 evidence deepen still open)
- Production deploy, Redis multi-tenant rate-limit platform, Kafka/Celery ingestion
- Shipping Alpha Vantage / Finnhub / Polygon in slice 1
- Web scraping of article bodies or full filing HTML (RSS headlines + EDGAR metadata only until XBRL slice)
- `scoring_agent` ADK / LLM “explaining” scores (2B is service-only)
- Ranking/screening, news/SEC-driven score adjustments
- Claiming “100% uptime” — reliability = honest gaps + richer fields

---

### Phase 0 data flow

```
User: "Analyze NVDA"
        │
        ▼
┌───────────────────────────┐
│ portfolio_research_agent  │  ADK root (Agent + analyze_ticker tool)
│ validate ticker           │
│ clear prior session keys  │  (5A — no cross-ticker contamination)
└─────────────┬─────────────┘
              │ ticker
              ▼
┌───────────────────────────┐
│ local result cache        │  key=normalized ticker
│ hit & not expired?        │
└───────┬─────────────┬─────┘
   HIT  │             │ MISS / expired
        ▼             ▼
  return cached   ┌───────────────────────────┐
  Phase0Result    │ yahoo + news + sec_edgar  │
  (skip tools +   │ (parallel; no LLM)         │
   LLM)           └─────────────┬─────────────┘
                                │ metrics + news + filings | ToolError
                                ▼
                  ┌───────────────────────────┐
                  │ evidence_from_metrics     │  PURE PYTHON
                  │ evidence_from_news        │
                  │ evidence_from_filings     │
                  │ + evidence_aggregator     │  dedupe / conflicts
                  └─────────────┬─────────────┘
                                │ EvidenceBundle (+ conflicts)
                                │ + metrics (for scoring)
                                ▼
                  ┌───────────────────────────┐
                  │ score_from_metrics (2B)   │  PURE PYTHON
                  │ FinancialMetrics→Scorecard│
                  └─────────────┬─────────────┘
                                │ Scorecard | null
                                ▼
                  ┌───────────────────────────┐
                  │ thesis_agent (+1 repair)  │  ONLY LLM step
                  └─────────────┬─────────────┘
                                │
                                ▼
                       Phase0Result JSON (+ optional scorecard)
                                │
                    status ok|partial ──▶ write cache (TTL clock starts)
```

### Shadow paths (required)

```
INPUT ──▶ VALIDATE ──▶ TOOL ──▶ EVIDENCE ──▶ AGGREGATE ──▶ SCORE ──▶ THESIS ──▶ OUTPUT
  │           │          │          │            │           │          │
  ▼           ▼          ▼          ▼            ▼           ▼          ▼
 nil/empty  bad ticker  timeout   empty data   (n/a)     null dims /  empty /
 ticker     → reject    empty     → bundle     pass-     scorecard=   uncited /
 → ask      loudly      payload   status=      through   null ok      dangling
 user                   → status  partial                             → error_code
                        =error                                        + evidence
```

| Path | Behavior | User sees |
|------|----------|-----------|
| Happy | Metrics → evidence → cited thesis (≥1 claim) | `status=ok` + JSON |
| Nil / blank ticker | Reject before tool call | Ask for ticker |
| Invalid ticker / not found | Tool returns not-found | `status=error`, `error_code=DATA_FETCH_FAILED` / `INVALID_TICKER` |
| Tool timeout / HTTP failure | No fabricated metrics | `status=error`, message |
| Empty / partial metrics | Evidence with nulls allowed; thesis only claims supported fields | `status=partial` |
| Thesis empty claims after repair | Model returned `claims: []` | `status=error`, `error_code=THESIS_EMPTY_CLAIMS`, evidence often present |
| Thesis omits / dangling citations | Invalid output after one repair | `status=error`, matching thesis `error_code`; not shipped |

---

### ADK mapping (Phase 0 only)

```
root_agent = Agent with analyze_ticker tool → run_phase0_research
  1. ensure_ticker + clear session keys (5A)
  2. cache_lookup (Python — hit returns Phase0Result, skip rest)
  3. fan-out: yahoo_finance + google_news + sec_edgar (thread pool)
  4. evidence_from_metrics / evidence_from_news / evidence_from_filings
  5. evidence_aggregator (dedupe, conflicts, status)
  6. score_from_metrics (2B — pure Python; optional scorecard on result)
  7. thesis_agent (LLM + one citation repair; aware of conflicts)
  8. cache_store (Python — only status ok|partial)
```

Rules:

- Prefer a single ADK tool + Python orchestrator for the research path.
- Do **not** require ADK `ParallelAgent` while fan-out lives in the pipeline service.
- Evidence builders, aggregator, scoring (2B), and cache are **services**, not reasoning agents.
- **Session (5A):** On each new research request, clear `financial_metrics`, `fundamentals`, `news_batch`, `filings_batch`, `evidence_bundle`, `scorecard`, `thesis`, `phase0_status`, then set `ticker`.
- Session state keys: `ticker`, `financial_metrics`, `fundamentals`, `news_batch`, `filings_batch`, `evidence_bundle`, `scorecard`, `thesis`, `phase0_status`, `cache_hit`.
- **ADK presentation:** Root agent must paste the **complete** `analyze_ticker` JSON (including `fundamentals`) before any prose summary.

---

### Local result cache (Phase 0)

File-backed, process-local (and durable across `adk` restarts on the same machine).

| Field | Value |
|-------|--------|
| Key | Normalized ticker (uppercase) |
| Value | Full `Phase0Result` JSON (`ok` or `partial` only — never cache `error`) |
| Store | Directory from settings, default `.cache/foliotracker/phase0/` (gitignored) |
| File | `{ticker}.json` plus `cached_at` ISO timestamp inside payload or sidecar |
| TTL | `PHASE0_CACHE_TTL_SECONDS` in settings (default **3600**) |
| Hit | If `now - cached_at < TTL` → return cached result with `cache_hit=true`; skip tools + thesis |
| Miss / expired | Full pipeline (`cache_hit=false`); on `ok`/`partial` write/overwrite cache and reset TTL clock |
| Invalidate | TTL expiry only in Phase 0 (no manual bust API yet) |
| Errors | Corrupt JSON / IO error → treat as miss, log warning, continue pipeline |

**Phase 2C note:** Result cache remains a coarse “skip whole pipeline” optimization. **Authoritative freshness** for live fetches is the per-source cache (ticker × `source_id`) so Yahoo, news, and SEC refresh on independent TTLs. A whole-result cache hit still short-circuits the pipeline today; finer invalidation (rebuild evidence/score/thesis when only some sources stale) remains a follow-up after 2C.3.

```
cache_lookup(ticker)
    │
    ├─ missing file ──────────────▶ MISS
    ├─ corrupt / IO error ────────▶ MISS (+ log)
    ├─ cached_at older than TTL ─▶ MISS (treat as invalidate)
    └─ fresh ─────────────────────▶ HIT → Phase0Result
```

Do **not** use Redis/Mongo for Phase 0. Do **not** share cache across machines.

---

### Evidence aggregator (Phase 1–2 contract)

Merge across financial + news + SEC filings. Still pure Python (no LLM).

```
FinancialMetrics ──▶ Evidence(type=financial, confidence=0.95)
NewsBatch        ──▶ Evidence(type=news, confidence=0.7) × N
SecFilingsBatch  ──▶ Evidence(type=sec, confidence=0.9) × N
        │
        ▼
  dedupe by (type, citation) or (type, normalized title)
  cap news to NEWS_MAX_ARTICLES (default 5, newest first)
  cap SEC to SEC_MAX_FILINGS (default 5, newest first)
  detect EvidenceConflict records (keyword heuristics)
        │
        ▼
EvidenceBundle(
  ticker,
  items=[Evidence, ...],
  conflicts=[EvidenceConflict, ...],
  status=ok|partial|error
)
```

**Status rules:** `error` only if zero items; `partial` if Yahoo metrics incomplete, news missing/failed, SEC missing/failed, or any conflicts; else `ok`.

---

### Scoring service (2B — shipped)

Pure Python. Input `FinancialMetrics` → `Scorecard`. No LLM. Optional `scorecard` on `Phase0Result`. Pipeline step after evidence aggregation, before thesis.

```
FinancialMetrics ──▶ score_from_metrics ──▶ Scorecard | null
```

| Field | Input | Direction (v1) | Clamp anchors |
|-------|--------|----------------|---------------|
| `growth_score` | `revenue_growth` | Higher growth → higher score | −0.50 → 0; +1.00 → 100 |
| `value_score` | trailing → `pe_ratio` → forward P/E | Lower positive P/E → higher score; non-positive → `null` | P/E 5 → 100; P/E 50 → 0 |
| `profitability_score` | `operating_margin` (fallback `gross_margin`) | Higher margin → higher score | −0.20 → 0; 0.50 → 100 |
| `risk_score` | `debt_to_equity` | Higher leverage → higher risk score | 0 → 0; 2.0 → 100 |
| `moat_score` | `gross_margin` | Provisional proxy only (weak) | 0 → 0; 0.80 → 100 |
| `execution_score` | — | Always `null` in v1 | — |

**Scale:** each dimension `0.0–100.0` or `null` (edges unit-tested).

**Partial honesty:** Missing metric → that dimension `null`; empty scorable inputs → `scorecard=null`. Scoring never invents numbers and never upgrades bundle status by itself.

**Out of thin 2B:** `scoring_agent` ADK, LLM score narratives, ranking/screening, portfolio risk, `sec_xbrl`, news/SEC-driven score adjustments.

**After thin Phase 2:** confidence calibration / graph edges later.

---

### Output schemas (Phase 0)

`Evidence` gains a stable `id` field (required for citations).

`InvestmentThesis` must support claim-level citations:

```
InvestmentThesis
  ticker: str
  thesis: str                    # short summary prose
  claims: list[ThesisClaim]      # material assertions
  bull_case / bear_case / key_risks / conviction  # optional in Phase 0
  evidence_ids: list[str]        # union of all claim citations

ThesisClaim
  text: str
  evidence_ids: list[str]        # min length 1 for material claims
```

`Phase0Result`:

```
Phase0Result
  ticker: str
  status: ok | partial | error
  evidence: EvidenceBundle | null
  thesis: InvestmentThesis | null
  scorecard: Scorecard | null   # 2B — optional; null when no scorable metrics
  fundamentals: FinancialMetrics | null  # 2C.2 — enriched snapshot for debug/report
  error_message: str | null   # user-readable; no exception class names
  error_code: str | null      # stable machine code (Phase0ErrorCode)
  disclaimer: str   # REQUIRED always — fixed non-advice copy (4A)
  cache_hit: bool   # REQUIRED always — true if served from local TTL cache (6A)
  request_id: str  # REQUIRED always — uuid correlating logs (9A)
```

`Scorecard` (existing schema; populated by 2B service):

```
Scorecard
  ticker: str
  growth_score / value_score / profitability_score: float | null  # 0–100
  moat_score / risk_score / execution_score: float | null          # 0–100
```

Fixed disclaimer copy (Phase 0):

> "FolioTracker output is for informational and educational purposes only. It is not investment, legal, or tax advice. Do your own research."

**Invariant:** If `status=ok` or `partial`, every `ThesisClaim.evidence_ids` entry exists in `evidence.items[].id`, and the thesis has ≥1 material claim. Enforced by schema validation + thesis agent + evals. `disclaimer`, `cache_hit`, and `request_id` are always set (including on `status=error`). On thesis-stage failure, `error_code` is one of `THESIS_EMPTY_CLAIMS` / `THESIS_UNCITED` / `THESIS_DANGLING_CITATION` / `THESIS_GENERATION_FAILED`, evidence may still be attached, thesis is null. On cache hit, generate a **new** `request_id` for this serve (do not reuse the cached request’s id); set `cache_hit=true`.

---

### Settings (Phase 0)

| Env / setting | Default | Purpose |
|---------------|---------|---------|
| `PHASE0_CACHE_TTL_SECONDS` | `3600` | Local result cache TTL |
| `PHASE0_CACHE_DIR` | `.cache/foliotracker/phase0` | Cache directory (gitignored) |
| `YAHOO_TIMEOUT_SECONDS` | `15` | Yahoo HTTP timeout (8A) |
| `NEWS_TIMEOUT_SECONDS` | `15` | Google News RSS timeout |
| `NEWS_MAX_ARTICLES` | `5` | Cap news evidence after dedupe |
| `SEC_TIMEOUT_SECONDS` | `15` | EDGAR HTTP timeout |
| `SEC_MAX_FILINGS` | `5` | Cap SEC evidence after dedupe |
| `SEC_USER_AGENT` | `FolioTracker contact@example.com` | Required by SEC fair-access; set a real contact email |
| `GOOGLE_API_KEY` | (required) | LLM |

### Security notes (Phase 0)

- Secrets only in `.env` (never logged; redaction in tool/HTTP error logs).
- Ticker validated to a strict pattern before tool call or prompt inclusion (e.g. `^[A-Z]{1,10}(\\.[A-Z]{1,3})?$`).
- Phase 1 news uses RSS headlines + URLs only (no article-body scrape → limited prompt-injection surface).
- Phase 2 SEC uses EDGAR filing metadata only (form, dates, accession, index URL) — no full-document scrape.
- Every `Phase0Result` includes the fixed `disclaimer` field (4A).

### Source trust

| Source | Confidence | Notes |
|--------|------------|-------|
| Yahoo Finance (financial metrics) | `0.95` fixed | Primary financial source today; day-1 enrich in 2C slice 2 |
| SEC EDGAR (filing metadata) | `0.9` fixed | Primary filings; metadata only in 2A |
| SEC XBRL (statement facts) | `0.95` planned | Phase 2C slice 3 — BS/CF/EPS truth; higher trust than commercial fill-gaps for statements |
| Google News (RSS headlines) | `0.7` fixed | Headlines only; lower trust than filings/metrics |
| Alpha Vantage (commercial) | `0.85` | OVERVIEW fill-gaps for forward/market fields; enabled when API key set |

**Cache note (Phase 1):** Bundle schema gained `conflicts`. Clear `.cache/foliotracker/phase0/` after upgrading if old cached JSON misbehaves; Pydantic defaults empty conflicts for missing keys.

**Cache note (Phase 2B):** `Phase0Result` gained optional `scorecard`. Clear `.cache/foliotracker/phase0/` after upgrading so cached results include scores (or explicit nulls).

**Cache note (fundamentals):** `Phase0Result` gained optional `fundamentals`. Clear `.cache/foliotracker/phase0/` after upgrading so cached results include the enriched snapshot (old cache loads with `fundamentals=null`).

---

### Interaction edge cases (Phase 0)

| Interaction | Edge case | Handled? | How |
|-------------|-----------|----------|-----|
| Ask research | Double message / re-submit same ticker | Y | 5A clear session; **cache hit** returns prior result within TTL |
| Ask research | New ticker while prior run in flight | Y | 5A clear session keys for new ticker; no shared bowl |
| Ask research | Navigate away mid-run (`adk web`) | Partial | Best-effort; orphan work ok in P0 |
| Cache | Expired entry | Y | Treat as miss; re-run pipeline; rewrite cache |
| Cache | Corrupt cache file | Y | Miss + warning log; do not crash |
| Tool call | Slow Yahoo (>30s) | Y | `ToolTimeoutError` → status=error |
| Thesis | Repair retry (3A) | Y | One shot then fail closed |
| Empty UX | Zero evidence | Y | status=error, disclaimer still set |
| Bad input | Garbage ticker | Y | `InvalidTickerError` before tool |

### Failure modes (named)

| Codepath | Failure | Exception / signal | Rescued? | User sees |
|----------|---------|--------------------|----------|-----------|
| ticker validate | empty / invalid format | `InvalidTickerError` | Y | ask / reject |
| `yahoo_finance` | timeout | `ToolTimeoutError` | Y → status=error | error JSON |
| `yahoo_finance` | HTTP / API error | `ToolUpstreamError` | Y → status=error | error JSON |
| `yahoo_finance` | unknown ticker | `TickerNotFoundError` | Y → status=error | error JSON |
| `yahoo_finance` | malformed payload | `ToolParseError` | Y → status=error | error JSON |
| evidence build | all metrics null | `EmptyMetricsError` | Y → status=partial or error | labeled |
| cache_lookup | corrupt / IO | warning + miss | Y → continue pipeline | transparent |
| cache_store | IO failure | log warning | Y → still return result (uncached) | ok result, no cache |
| thesis_agent | empty claims list | `EmptyClaimsError` | Y → **retry once** (must keep ≥1 claim when evidence exists); still empty → `status=error`, `error_code=THESIS_EMPTY_CLAIMS` | user message + evidence |
| thesis_agent | uncited claims | `UncitedClaimError` | Y → **retry once** (“cite or remove that claim”); still bad → `status=error`, `error_code=THESIS_UNCITED` | user message + evidence |
| thesis_agent | dangling evidence_ids | `DanglingCitationError` | Y → reject; `status=error`, `error_code=THESIS_DANGLING_CITATION` | user message + evidence |
| thesis_agent | empty / refuse | `ThesisGenerationError` | Y → `status=error`, `error_code=THESIS_GENERATION_FAILED` | user message + evidence |

Catch-all `except Exception` is **not** acceptable in tools or aggregator.

**Thesis citation policy (3A):** On `EmptyClaimsError`, `UncitedClaimError`, or dangling citation failure, re-invoke `thesis_agent` once with repair instructions (cite valid ids; do not return an empty claims list when evidence exists). If the second output still has empty claims, uncited material claims, or dangling IDs → `Phase0Result.status=error` with the matching `error_code`, no thesis shipped; evidence may still be attached for debuggability.

---

### Test coverage map (Phase 0)

```
NEW UX FLOWS:
  ask ticker → Phase0Result (live)
  ask same ticker within TTL → cache_hit=true
  ask after TTL → live refresh

NEW DATA FLOWS:
  ticker → yahoo → metrics → evidence → bundle → thesis → result → cache write
  ticker → cache hit → result

NEW CODEPATHS:
  validate ticker / 5A session clear
  cache lookup hit|miss|expired|corrupt
  tool errors (timeout, not found, parse)
  empty/partial metrics
  thesis citation repair once then fail
  disclaimer + cache_hit always set

NEW BACKGROUND JOBS: none

NEW INTEGRATIONS: Yahoo Finance HTTP

NEW ERROR/RESCUE PATHS: see Failure modes table
```

**Friday 2am test:** fixture bundle → thesis cites only fixture IDs; empty bundle → no invented numbers.  
**Hostile QA:** prompt stuffing in ticker (rejected); corrupt cache file; TTL boundary (−1s / +1s).  
**Chaos:** Yahoo timeout mid-run → status=error, nothing written to cache.

### Eval & test strategy (before implementation)

Hard gate: you review these artifacts before any tool/agent implementation code.

**Unit tests (no LLM):**

- Ticker validation (nil, empty, bad format, ok)
- Yahoo tool mock → `FinancialMetrics` parse / errors
- Metrics → `Evidence` + stable id
- Aggregator pass-through bundle
- Schema invariant: claim evidence_ids ⊆ bundle ids
- Cache: miss, hit within TTL (`cache_hit=true`), expired miss, corrupt file → miss
- Cache: never stores `status=error`; cached payloads re-served with `cache_hit=true`
- Session 5A: new ticker clears prior evidence/thesis keys
- Disclaimer always present on Phase0Result (including errors)
- `request_id` always present; new uuid on cache hit serves
- `cache_hit` always present

**Evals (LLM thesis path):**

- Golden tickers with fixture `EvidenceBundle` → thesis must cite only those IDs
- Hostile cases: empty bundle → must not invent metrics
- Partial metrics → claims only on present fields
- Rubric: groundedness, citation coverage, no fabricated numbers
- **Runner (7A):** on-demand script under `evaluations/phase0/` — **not** in default CI
- **CI:** unit tests only (`tests/unit/`)

Suggested layout (Phase 0 core; later phases added more unit files):

```
tests/
  unit/
    test_ticker.py
    test_yahoo_finance_parse.py
    test_evidence_from_metrics.py   # also aggregator / news / filings evidence
    test_thesis_schema_invariants.py
    test_phase0_cache.py
    test_session_clear.py
    test_google_news.py / test_sec_edgar.py / test_scoring.py
    test_source_registry.py / test_source_cache.py / test_source_fetch.py
    test_phase0_pipeline.py / test_agent_output_contract.py
evaluations/
  phase0/
    cases/
      happy_nvda.json
      partial_metrics.json
      empty_bundle.json
    rubrics/
      groundedness.md
    README.md          # how to run; pass criteria; CI=unit only (7A)
```

Default CI / `pytest` = `tests/unit/` only. LLM evals are an explicit on-demand command.
Implementation starts only after explicit approval of flows + evals.

---

### Deployment & rollout (Phase 0)

Phase 0 ships **locally** via `adk web` / `adk run app`. No cloud deploy, no migrations, no feature flags.

```
Install deps → cp .env.example .env → set GOOGLE_API_KEY
    → pytest tests/unit
    → (optional) on-demand LLM evals
    → adk web
```

**Rollback:** git revert / restore previous `app/` + clear `.cache/foliotracker/phase0/` if bad cached theses.  
**Post-start smoke:** analyze one known ticker (e.g. AAPL); confirm `status`, `disclaimer`, `request_id`, citations.  
**Deploy-time dual-version:** N/A (single local process).  
**Repo hygiene:** add `.cache/` to `.gitignore` (obvious fix — will land with tests/impl prep).

### Observability (Phase 0 — minimal)

No dashboards or pagers in Phase 0. Debuggability via structured logs + result fields.

| Signal | What |
|--------|------|
| Log: pipeline start | ticker, request_id (uuid) |
| Log: cache hit/miss/expired | ticker, cache_hit, age_s |
| Log: yahoo outcome | ticker, latency_ms, ok\|error class |
| Log: thesis attempt | ticker, attempt 1\|2, citation_ok |
| Log: pipeline end | ticker, status, cache_hit, latency_ms |
| Result fields | `status`, `cache_hit`, `disclaimer`, `error_message`, `request_id` |
| Secrets | Never log API keys or full `.env` |

**Not in Phase 0:** metrics backends, distributed tracing, alerting, admin UI.

### Performance notes (Phase 0)

| Path | Expected p99 (order of magnitude) | Notes |
|------|-----------------------------------|--------|
| Cache hit | <50ms | Local file read + JSON parse |
| Yahoo fetch | 1–5s typical; hard timeout **15s** (`YAHOO_TIMEOUT_SECONDS`, 8A) | On timeout → `ToolTimeoutError` |
| evidence + aggregate | <10ms | Pure Python |
| thesis_agent (+ optional repair) | 5–30s | Dominates live path |
| Live end-to-end | ~Yahoo + thesis | Cache collapses repeat cost |

No N+1 DB (no DB). No connection pool beyond HTTP client for Yahoo. Cache files unbounded by ticker count in P0 — acceptable for local use; do not build eviction beyond TTL.

### Phase 0 sequence (build order)

```
1. Update schemas (Evidence.id, ThesisClaim, Phase0Result + disclaimer/cache_hit/request_id)
2. Land unit tests + eval fixtures/rubrics (incl. cache TTL + session clear)
3. Human review: architecture flows + evals                  ← YOU
4. Implement yahoo_finance tool
5. Implement evidence_from_metrics + aggregator + local cache
6. Implement thesis_agent + root SequentialAgent (5A session clear)
7. Run evals; fix until green
```

Steps 4–7 do not begin until step 3 is approved.

---

## Target platform — Portfolio Intelligence (adopted north star)

The adopted target (2026-08-05, superseding the earlier capability-oriented cathedral): **six engines over one evidence spine**, each engine a composition of deterministic services plus narrowly-scoped LLM reasoning — never a parallel data stack. Build only the slice currently sequenced in [TODOS.md](../TODOS.md).

```
                        Busy professional, every morning
                                     │
     ┌───────────────────────────────┼───────────────────────────────┐
     ▼                               ▼                               ▼
 Brief page (shipped)          Thesis page (planned)          Watchlist / Risk (shipped)
 Engine 1                      Engines 2–6
 Market Intelligence           Fundamental │ Valuation │ Framework
                               Thesis Monitoring │ AI Advisor
     │                               │                               │
     └───────────────────────────────┼───────────────────────────────┘
                                     ▼
                    Deterministic service layer (no LLM math)
        scoring · framework engines · valuations · net assets · OS Score
                                     │
                                     ▼
              Evidence spine: builders → aggregator → citations
                                     │
                                     ▼
        merge_fundamentals + provenance (trust ladder, honest gaps)
                                     │
                                     ▼
      source_registry / per-source cache / cached_fetch (TTL + budgets)
                                     │
              ┌──────────┬───────────┼───────────┬──────────┐
              ▼          ▼           ▼           ▼          ▼
            yahoo    google_news  sec_edgar   sec_xbrl  alpha_vantage
```

LLM steps stay narrow and fail-closed: `thesis_agent` (cited research thesis), insight providers (`brief_insight`, planned thesis advisor/explain) — always provider-labeled, never arithmetic.

**Deferred beyond the engine map** (recorded, not sequenced): future framework modules (Marks, Munger, Mauboussin, Fama-French, Behavioral, Macro Overlay — PRD §5.4.13), Brief dissemination adapters, social display-only ingest, memory layers beyond TTL files, full evidence graph edges, hosted multi-tenant deploy (Phase 3).

---

## Long-term trajectory (Phase 0 → later)

| Dimension | Rating / note |
|-----------|----------------|
| Reversibility | **5/5** — local only, file cache, no migrations |
| Tech debt introduced | Intentional stubs for unused agents; Phase 0 must not pretend they’re live |
| Path dependency | Evidence + citation spine is the load-bearing choice — good |
| 1-year readability | Phase 0 section at top of this doc is the on-ramp |

**Current position (2026-08-06):** spine + watchlist + Risk v2 + Brief (Engine 1) + intake shipped; next is Brief dogfood Assignment, then Thesis T1 (Engines 2–6 begin).

## Dream state delta

| Now | After Thesis T1–T5 | Full Portfolio Intelligence |
|-----|--------------------|-----------------------------|
| Evidence spine (Yahoo + news + SEC + XBRL + AV), cited thesis, Scorecard, watchlist/Risk, Brief triage dashboard (Engine 1), intake | Thesis page hosting Engines 2–6: framework scorecards, valuation ladder, net assets, thesis monitoring, advisor, OS Score; Brief E1 count strip | All six engines mature; future framework modules; dissemination; memory; hosted deploy (Phase 3) |

Phase 0–2C proved the spine. Brief proved the engine template (schemas → deterministic services → ring store → API → page). Thesis reuses that template for Engines 2–6 without pretending the full platform is built.

---

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 1 | CLEAR | mode: SCOPE_REDUCTION; Phase 0 thin slice; 0 critical gaps left open |
| Codex Review | `/codex review` | Independent 2nd opinion | 0 | — | — |
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 1 | CLEAR (PLAN) | Phase 2C B1 locked; 4 issues closed into design; 0 critical gaps |
| Design Review | `/plan-design-review` | UI/UX gaps | — | — | Dashboard v1 design locked in plan (navy/paper/copper; Fraunces + IBM Plex) |

**UNRESOLVED:** 0  
**VERDICT:** CEO + ENG CLEARED — Phase 2C + watchlist dashboard v1 shipped.

### Eng review notes (2026-07-25 — Phase 2C)

**Step 0:** Scope reduced to docs + sliced impl (not full Kafka platform). Approach B1 accepted via office-hours.

**Architecture (issues closed into design):**
1. Whole-result TTL cannot control per-source frequency → per-source cache
2. Yahoo-fatal blocks resilience → soften only after merge + min fields (2C.3)
3. Thin `FinancialMetrics` insufficient for ritual → `FundamentalsSnapshot` + Yahoo enrich
4. Secondary provider priority → SEC XBRL before Alpha Vantage

**Code quality:** Prefer wrapping existing tools over parallel ingestion paths; keep merge/provenance explicit (no clever silent coalesce).

**Test coverage plan (impl):**

```
CODE PATH COVERAGE (Phase 2C)
===========================
[+] source_registry / source_cache / source_fetch
    ├── [★★  TESTED] hit / miss / expired / corrupt / rate budget — unit tests
    └── [GAP] pipeline integration under rate-limit + stale Yahoo — thin

[+] merge_fundamentals (2C.3)
    ├── [GAP] fill-nulls by trust — NO TEST YET (feature not built)
    ├── [GAP] field disagreement → conflict — NO TEST YET
    └── [GAP] never invent values — NO TEST YET

[+] phase0_pipeline (source-aware)
    ├── [★★  TESTED] Yahoo+news+SEC fan-out + fundamentals attach — test_phase0_pipeline.py
    ├── [GAP] independent source refresh vs whole-result TTL
    └── [GAP] Yahoo fail + merge enough → partial (2C.3)

USER FLOW COVERAGE
===========================
[+] Analyze ticker (adk)
    ├── [★★  TESTED] Happy / partial / Yahoo error (current) — unit + evals
    ├── [~] Root agent full-JSON instruction contract — test_agent_output_contract.py
    ├── [GAP] [→E2E] Re-analyze with staggered source TTLs
    └── [GAP] Dogfood field checklist (3 tickers) — manual acceptance

─────────────────────────────────
COVERAGE: 2C.1–2C.2 unit-covered; 2C.3 + cache-interaction paths remain GAPs
─────────────────────────────────
```

**Performance:** Per-source cache cuts redundant Yahoo/news/SEC calls; watch unbounded source cache files (same local-only acceptance as Phase 0). No N+1 DB.

**NOT in scope / What already exists:** See Phase 2C section above and TODOS.md.

**Parallelization:** Phase 2C + dashboard + Risk v2 + Brief Slice 1 done. Next: Brief dogfood / intake / Phase 3 deepen.

---

## Engine 1 — Daily Decision Brief (shipped)

Portfolio-scoped material-event triage over **Held ∪ Watched** (Held wins duplicates). Slice 1 shipped 2026-08-03; triage dashboard shipped 2026-08-04. **This is the Engine 1 (Market Intelligence) surface of Portfolio Intelligence — its contracts, generator, and UI are preserved unchanged.** The only queued change is the additive, backwards-compatible Brief E1 enrichment (after Thesis T3).

### Data flow

```
membership snapshot
  → bounded pool (4–8) per ticker:
        cached_fetch yahoo → history_closes → last-session daily %
        cached_fetch news + SEC → evidence_from_* → brief_classify
  → gate: |daily return| ≥ 5% OR classified event (24h window)
  → rank max(move_score, event_severity); Impact Score (0–100) + High/Medium/Quiet priority
  → insight provider (BRIEF_INSIGHT_MODE: deterministic | canned | llm, fail-closed)
  → cap 15 tickers / 5 bullets
  → brief_store ring-14 + DailyBrief JSON
  → GET/POST /api/brief* + BriefPage triage dashboard (PrimaryNav)
```

**Does not** call `run_phase0_research`. Phase0 cache is optional for the metrics strip (P/E, 1Y, G/V/R).

### Contracts

| Piece | Role |
|-------|------|
| `DailyBrief` / `BriefTicker` / `BriefBullet` / `BriefInsight` | `app/schemas/brief.py` — triage fields (`impact_score` 0–100, priority, category, severity), structured insight (what happened / why / market reaction / should long-term care), `insight_mode` provider label |
| `yahoo_history` | Shared parse + last-session daily % + `move_score` (Risk + Brief) |
| `brief_classify` | Keyword + SEC form heuristics → category/severity |
| `brief_service.generate_daily_brief` | Sync Generate; ~60s wall → `generation_status` complete/stale/partial |
| `brief_insight` | Insight provider: `BRIEF_INSIGHT_MODE=deterministic` (default) \| `canned` \| `llm`; llm fails closed to deterministic; provider label always on payload |
| `brief_store` | Ring-14 JSON (history browse) + miss-log JSONL |
| API | `GET /api/brief`, `GET /api/brief/history`, `POST /api/brief/generate`, `POST /api/brief/miss`, `POST /api/brief/explain` |
| UI | `BriefPage` triage dashboard — High/Medium/Quiet inbox rows, filters, quiet list, morning digest strip, history timeline, heat map, stock drawer, miss log |

### Yahoo `history_closes`

`FinancialMetrics.history_closes` is populated by Yahoo `metrics_from_bundle` and persisted in the Yahoo source cache so Risk correlations and Brief daily % share one series. Excluded from evidence serialization (ID stability).

### Out of current Brief scope

Scheduled generation, social display-only section, earnings-call digests, dissemination adapters (email / messaging / audio / MCP — recorded, not built until the website Brief is trusted). Brief E1 enrichment (optional `BriefBullet` fields + morning count strip) is queued **after** Thesis T3 and must stay backwards-compatible.

---

## Flexible ticker intake (shipped 2026-08-03)

Bulk membership intake without one-by-one typing: CSV / free-text paste / screenshot-OCR text / speech transcript all feed one extract path. Membership-first — **no auto-research on bulk add** (preserves the watchlist cost model).

| Piece | Role |
|-------|------|
| Extract + normalize service | Parse unstructured text → candidate tickers; validate via existing strict ticker rules; never invent symbols from OCR/speech noise (fail closed on empty extract) |
| `WatchlistIntakeRequest` / `WatchlistIntakeResponse` | `app/schemas/watchlist.py` — text + target list kind → `added` / `skipped_duplicate` / `rejected_invalid` |
| API | `POST /api/watchlist/intake` — idempotent: tickers already in Held ∪ Watched are skipped (no error, no list move) |
| UI | CSV file picker + paste area; screenshot and mic are capture affordances into the same extract path |

---

## Portfolio Intelligence — Thesis page (Engines 2–6, planned)

Docs locked 2026-08-05. Product frame: [PRD](PRD.md) §1 (six engines) and §5.4 (Thesis landing page, normative examples). Slices T1–T5 + Brief E1 sequenced in [TODOS.md](../TODOS.md).

**Engine → surface mapping:** Engine 1 (Market Intelligence) = the shipped Brief, **unchanged** — everything in the "Engine 1 — Daily Decision Brief" section above remains authoritative. Engines 2–6 (Fundamental, Valuation, Framework, Thesis Monitoring, Advisor) = the new Thesis page, built on the same evidence spine and the Brief architectural template (schemas → deterministic services → ring store → HTTP API → Svelte page).

### Data flow (planned)

```
membership snapshot (Held ∪ Watched)
  → per ticker (bounded pool, cache-first):
        merged fundamentals (Yahoo + SEC XBRL via cached_fetch / phase0 cache)
        → fundamental metrics (incl. Altman Z / Piotroski F / Beneish M where computable)
        → valuation service (Graham / Buffett / Modern sets → six-value ladder)
        → framework engine (deterministic per-framework scorecards)
        → net asset service (asset breakdown → adjusted net assets)
  → thesis snapshot store (per-ticker ring): diff vs prior quarter
        → change verdict: No change | Strengthened | Slightly weaker | Broken
  → advisor insight (THESIS_INSIGHT_MODE, fail-closed) + Investment OS Score
  → GET/POST /api/thesis* → ThesisPage (PrimaryNav: Watchlist | Risk | Brief | Thesis)
```

Like Brief, Generate does **not** call `run_phase0_research`; it composes over cached sources and merged fundamentals. The existing Phase 0 `InvestmentThesis` (from `thesis_agent`) seeds each ticker's original thesis for monitoring.

### Contracts (planned — `app/schemas/thesis.py`)

| Piece | Role |
|-------|------|
| `FrameworkScorecard` / `FrameworkCheck` | Per-framework score (0–100 or null) + named checks (PASS / value / rating); cites the fundamentals fields consumed |
| `ValuationSet` | Graham / Buffett / Modern valuations + six-value ladder (Market / Intrinsic / Liquidation / Replacement / Enterprise / Expected Fair); null per method when unsupported |
| `AssetBreakdown` | Assets − liabilities → Adjusted Net Assets; vs market cap delta |
| `ThesisSnapshot` / `ThesisChange` | Point-in-time thesis + framework/valuation state; quarterly diff → closed verdict set |
| `AdvisorInsight` | Reasoning lines + directive conclusion + confidence + provider label |
| `InvestmentOSScore` | Deterministic composite from the locked weight table (PRD §5.4.11) |
| `ThesisDashboard` | Portfolio rollup counts (health, strong/weak balance sheets, value traps, under/overvalued, conviction, thesis broken) |
| Store | Per-ticker ring JSON (like `brief_store`); path/env below |
| API | `GET /api/thesis`, `POST /api/thesis/generate`, `POST /api/thesis/explain` |
| UI | `ThesisPage` + `thesis/*` components (see [DESIGN.md](../DESIGN.md)) |

### Settings (planned — mirror Brief conventions)

| Env | Purpose |
|-----|---------|
| `THESIS_INSIGHT_MODE` | `deterministic` (default) \| `canned` \| `llm`; llm fail-closed to deterministic |
| `THESIS_STORE_PATH` | Snapshot ring store (default under `.cache/foliotracker/`) |
| `THESIS_GENERATE_BUDGET_SECONDS` / `THESIS_MAX_WORKERS` | Wall budget + bounded pool |

### Framework formula specs (LOCK BEFORE T1 IMPLEMENTATION)

Per [PRD open question 6](PRD.md) (default adopted): every framework's formulas and thresholds are locked **here** as a spec table — with unit tests — before any agent or service consumes its scores (same invariant as the 2B scoring service). T1 covers **Graham** and **Financial Strength**; remaining frameworks add their tables when their slice is designed.

Table skeleton per framework (filled at T1 design; placeholders below are illustrative, not locked):

| Check | Input fields (merged fundamentals) | Formula / threshold | Result type | Missing-input behavior |
|-------|------------------------------------|---------------------|-------------|------------------------|
| e.g. Margin of Safety | intrinsic value, market price | *TBD at T1 design* | % + rating | `null` + "insufficient data" |
| e.g. Current Ratio | `balance_sheet.*` | *TBD at T1 design* | value + PASS/FAIL | `null` |
| **Framework score** | check results | weighted composite, 0–100 *(weights TBD)* | 0–100 or `null` | `null` when below minimum check coverage |

- **Graham Deep Value** — checks per PRD §5.4.3 (Margin of Safety, Net-Net, Current Ratio, Debt, Earnings Stability, Dividend History): *table pending T1 design*
- **Financial Strength** — checks TBD (candidates: leverage, coverage, liquidity, Altman Z / Piotroski F when computable): *table pending T1 design*
- Lynch, Greenblatt, Quality, GARP, Dividend, Momentum, Buffett: phase-next; tables land with their slices

### Engineering invariants (restated for this track)

- **Deterministic math first:** every framework formula, valuation, and the OS Score composite is a pure-Python service with unit tests **before** any agent consumes it. LLMs never perform score/valuation arithmetic.
- **LLM scope:** thesis-change narrative, advisor reasoning, and research-button answers only — structured output, fail-closed, provider label always on the payload (same pattern as `brief_insight`).
- **Honest gaps:** unsupported metrics/valuations are `null` with an "insufficient data" label; Replacement Value ships `null` until a method is locked (PRD open question).
- **Advice stance ripple:** directive phrasing (buy more / hold / trim / research / wait) is allowed **only** in `AdvisorInsight`. Brief, Watchlist, and Risk stay non-directive; the fixed disclaimer remains on every result and surface.
- **Brief preservation:** no shipped Brief schema/service/API/UI contract changes. Brief E1 adds **optional** `BriefBullet` fields (impact, confidence, affected_frameworks, thesis_impact) + a morning count strip — backwards-compatible, sequenced after T3.

---

## Changelog

| Date | Change |
|------|--------|
| 2026-08-06 | Align doc to Portfolio Intelligence platform (PRD 2026-08-05): reframed header/status, principles 6–7 (frameworks-as-lenses, Advisor-only directive guidance), platform-level six-engine map, Brief section refreshed to shipped triage dashboard (history/explain/insight modes) as Engine 1 surface, flexible intake section added, framework formula-spec lock placeholder (pre-T1 gate), six-engine target architecture replaces deferred cathedral north star |
| 2026-08-05 | Portfolio Intelligence (planned): Thesis page section — engines 2–6 data flow, `app/schemas/thesis.py` contracts, `THESIS_*` settings, invariants; Brief preserved unchanged as Engine 1 surface |
| 2026-08-03 | Daily Decision Brief Slice 1: schemas, classify, yahoo_history, generator, API, BriefPage; `history_closes` on Yahoo cache |
| 2026-07-31 | Correlation slice (Risk v2): pairwise ~1y returns from Yahoo source-cache `history_closes`; `PairCorrelation` on `GET /api/risk` |
| 2026-07-30 | Portfolio Risk v1: Held equal-weight concentration (`GET /api/risk`, `RiskPage`, design 7A nav) |
| 2026-07-25 | Watchlist dashboard v1: FastAPI + Svelte 5 over Phase0Result (local JSON membership) |
| 2026-07-25 | Alpha Vantage fill-gaps shipped: OVERVIEW → `forward_pe`/market fields; optional key; soft-fail |
| 2026-07-25 | Phase 2C.3 shipped: `sec_xbrl`, `merge_fundamentals`, soften Yahoo-fatal via min field checklist |
| 2026-07-25 | Lock 2C.3 min fundamentals paths (`fundamentals_minimum.py`); soften Yahoo only when checklist passes |
| 2026-07-25 | Doc hygiene: PRD/TODOS/architecture status aligned to 2C.1–2C.2 shipped; 2C.3 next |
| 2026-07-25 | Phase0Result.fundamentals + root agent must emit full JSON for debug |
| 2026-07-25 | Phase 2C.2 shipped: enriched `FinancialMetrics` / `FundamentalsSnapshot`; Yahoo profile, returns, BS/CF, forward P/E |
| 2026-07-25 | Phase 2C.1 shipped: `source_registry` / `source_cache` / `cached_fetch`; pipeline fan-out per-source |
| 2026-07-25 | Phase 2C design locked (B1): provider port, per-source cache, Yahoo enrich → SEC XBRL → AV/FMP; local rate budgets in scope |
| 2026-07-24 | Phase 2B shipped: `score_from_metrics`, `Phase0Result.scorecard`, clamp anchors documented |
| 2026-07-24 | Lock 2B scoring contract: dimensions, Scorecard on Phase0Result, service-only (no scoring_agent) |
| 2026-07-24 | Thesis empty-claims taxonomy: `EmptyClaimsError`, `Phase0ErrorCode`, user-readable thesis errors |
| 2026-07-24 | Phase 2A: SEC EDGAR specialist (metadata) on evidence spine |
| 2026-07-24 | Thin Phase 2 lock: SEC (2A) → scoring (2B); portfolio/memory deferred |
| 2026-07-24 | Link product PRD from Related docs |
| 2026-07-24 | Phase 1: Google News specialist, aggregator merge/conflicts, JSON disagreement surface |
| 2026-07-21 | CEO review complete (REDUCTION): TODOS.md for Phase 1+; `.cache/` gitignored |
| 2026-07-21 | CEO review: Phase0Result.request_id required (9A); new id on cache hit serves |
| 2026-07-21 | CEO review: YAHOO_TIMEOUT_SECONDS=15 (8A); CI unit-only (7A); minimal structured logs |
| 2026-07-21 | CEO review: CI = unit tests only; LLM evals on-demand (7A) |
| 2026-07-21 | CEO review: Phase0Result.cache_hit required (6A) |
| 2026-07-21 | CEO review: session clear (5A) + local TTL file cache for Phase0Result |
| 2026-07-21 | CEO review: required disclaimer on Phase0Result (4A); ticker format validation + log redaction noted |
| 2026-07-21 | CEO review: uncited claims → one repair retry then fail closed (3A) |
| 2026-07-21 | CEO review: metrics→Evidence is pure Python service (2A); thesis_agent is sole LLM step |
| 2026-07-21 | CEO review (SCOPE REDUCTION): Phase 0 thin slice, flows, failures, eval-first gate; cathedral deferred |
| 2026-07-14 | Initial capability-oriented architecture draft |
