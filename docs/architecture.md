# FolioTracker Architecture

AI portfolio / stock research on [Google ADK](https://adk.dev/).

**Status:** Thin Phase 2 **complete** (2A SEC + 2B scoring). Portfolio/memory deferred. See [TODOS.md](../TODOS.md).

**Related:** [PRD.md](PRD.md) · [implementation-status.md](implementation-status.md) · [TODOS.md](../TODOS.md)

---

## Design principles (non-negotiable)

1. **Agents reason; tools fetch; services calculate.** Agents must not perform HTTP or arithmetic.
2. **Schemas are the contracts.** No free-form agent output as the system of record.
3. **Evidence over vibes.** Downstream agents consume `Evidence`, not raw prose from upstream agents.
4. **Eval-first.** Tests and evals are written and reviewed before implementation code for each phase.
5. **Partial failure is visible.** Missing data yields a degraded, labeled result — never a silent fake thesis.

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

`sec_xbrl` stays stubbed. Portfolio/memory stay deferred (see TODOS). Thin Phase 2 complete = 2A + 2B.

### Explicitly NOT in scope (beyond thin Phase 2)

- Technical / social / macro agents
- ADK `ParallelAgent` rewrite (fan-out stays in the Python pipeline)
- Full evidence graph edges / confidence calibration
- XBRL fact extraction (`sec_xbrl`)
- Memory layers, Mongo, vector store (local TTL file cache **is** in Phase 0 — see below)
- Portfolio / correlation / multi-ticker risk
- Custom HTTP API / UI beyond `adk web`
- Production deploy, dashboards, rate-limit platform
- Web scraping of article bodies or full filing HTML (RSS headlines + EDGAR metadata only)
- `scoring_agent` ADK / LLM “explaining” scores (2B is service-only)
- Ranking/screening, news/SEC-driven score adjustments

---

### Phase 0 data flow

```
User: "Analyze NVDA"
        │
        ▼
┌───────────────────────────┐
│ portfolio_research_agent  │  ADK root (SequentialAgent or equiv.)
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
- **Session (5A):** On each new research request, clear `financial_metrics`, `news_batch`, `filings_batch`, `evidence_bundle`, `scorecard`, `thesis`, `phase0_status`, then set `ticker`.
- Session state keys: `ticker`, `financial_metrics`, `news_batch`, `filings_batch`, `evidence_bundle`, `scorecard`, `thesis`, `phase0_status`, `cache_hit`.

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
| `value_score` | `pe_ratio` | Lower positive P/E → higher score; non-positive → `null` | P/E 5 → 100; P/E 50 → 0 |
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
| Yahoo Finance (financial metrics) | `0.95` fixed | Primary financial source |
| SEC EDGAR (filing metadata) | `0.9` fixed | Primary filings; metadata only in 2A |
| Google News (RSS headlines) | `0.7` fixed | Headlines only; lower trust than filings/metrics |

**Cache note (Phase 1):** Bundle schema gained `conflicts`. Clear `.cache/foliotracker/phase0/` after upgrading if old cached JSON misbehaves; Pydantic defaults empty conflicts for missing keys.

**Cache note (Phase 2B):** `Phase0Result` gained optional `scorecard`. Clear `.cache/foliotracker/phase0/` after upgrading so cached results include scores (or explicit nulls).

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

Suggested layout:

```
tests/
  unit/
    test_ticker.py
    test_yahoo_finance_parse.py
    test_evidence_from_metrics.py
    test_aggregator.py
    test_thesis_schema_invariants.py
    test_phase0_cache.py
    test_session_clear.py
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

## Target platform (DEFERRED — 12-month ideal)

Capability-oriented OS: many specialists, shared workflows, evidence graph, scoring, memory, portfolio layer. Useful as north star; **do not implement in Phase 0**.

```
                           User Request
                                │
                                ▼
                    Portfolio / Stock Research Agent
                                │
                    (Planning & Orchestration)
                                │
          ┌───────────────┬───────────────┬───────────────┐
          ▼               ▼               ▼               ▼
    Company Domain   Financial Domain   Market Domain   Governance
                                │
                        Shared Workflows
                                │
                     Shared Tool & Service Layer
                                │
                         Evidence Repository
                                │
                      Scoring / Analytics Services
                                │
                         Report Generation Agent
```

### Deferred capability map (scaffold may exist; not Phase 0 work)

```
agents/     orchestrator/, company/, financials/, market/,
            technical/, governance/, report/
tools/      finance/, filings/, search/, web/, news/, social/,
            ai/, cache/, persistence/
workflows/  search_extract, filing_analysis, earnings_*, …
services/   valuation, scoring, ranking, normalization, caching
memory/     research, ticker, company, session, portfolio
```

Future composition (when Phase 0 is done): ETF, dividend, M&A, earnings preview, portfolio risk agents reuse the same evidence spine — after aggregator grows beyond pass-through.

---

## Long-term trajectory (Phase 0 → later)

| Dimension | Rating / note |
|-----------|----------------|
| Reversibility | **5/5** — local only, file cache, no migrations |
| Tech debt introduced | Intentional stubs for unused agents; Phase 0 must not pretend they’re live |
| Path dependency | Evidence + citation spine is the load-bearing choice — good |
| 1-year readability | Phase 0 section at top of this doc is the on-ramp |

**After thin Phase 2 shipped (2A + 2B):** portfolio/memory deferred (see TODOS).

## Dream state delta

| Now | After thin Phase 2 | 12-month ideal |
|-----|--------------------|----------------|
| Yahoo + news + SEC cited thesis + conflicts + Scorecard | (shipped) Multi-domain spine + deterministic scores | Full evidence graph, portfolio, scoring, memory |

Phase 0 moves toward the ideal by proving the spine. It does not pretend the cathedral is built.

---

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 1 | CLEAR | mode: SCOPE_REDUCTION; Phase 0 thin slice; 0 critical gaps left open |
| Codex Review | `/codex review` | Independent 2nd opinion | 0 | — | — |
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 0 | — | — |
| Design Review | `/plan-design-review` | UI/UX gaps | 0 | — | SKIPPED (no custom UI) |

**UNRESOLVED:** 0  
**VERDICT:** CEO CLEARED (REDUCTION) — eng review recommended before implementation; next build step is schemas + tests/evals for human review gate.

---

## Changelog

| Date | Change |
|------|--------|
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
