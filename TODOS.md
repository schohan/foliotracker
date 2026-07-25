# TODOS

Deferred work from CEO plan review (2026-07-21) and eng/office-hours design (2026-07-25). Phase 1–2B shipped. Phase 2C multi-source ingestion **designed** (Approach B1) — see [docs/architecture.md](docs/architecture.md).

**Phase 2 lock (2026-07-24):** Thin Phase 2 = **SEC specialist → scoring service**. Portfolio and cache/memory deferred.

**Thin Phase 2 complete** = 2A + 2B (**both done 2026-07-24**).

**Phase 2C lock (2026-07-25):** Provider port + per-source cache; Yahoo enrich day-1; SEC XBRL next; Alpha Vantage/FMP later. No Kafka.

## Phase 2C — Multi-source ingestion

### Soften Yahoo-fatal + SEC XBRL fundamentals (2C.3)

**What:** Merge policy so Yahoo failure alone can yield `partial` when another fundamentals source filled enough fields; implement `sec_xbrl` as first secondary fundamentals provider for BS/CF/EPS truth.

**Why:** Reliability and statement accuracy; SEC is the logical source for audited statements. Soften hard-fail only after merge + minimum-field rules exist.

**Context:** Today Yahoo errors abort the pipeline in `phase0_pipeline`. Enriched Yahoo snapshot exists (2C.2). `sec_xbrl` is stubbed. Prefer SEC over Alpha Vantage for statements. Minimum field set for “enough fundamentals” is an open PRD question. Add `merge_fundamentals` with field provenance.

**Effort:** L  
**Priority:** P1  
**Depends on:** 2C.1 + 2C.2 (done); open question on minimum field set

### Alpha Vantage / FMP forward-estimate fill-gap

**What:** Optional commercial provider for forward P/E / estimates when Yahoo gaps remain after SEC XBRL.

**Why:** Forward metrics are part of the ritual; SEC filings do not replace analyst forward P/E.

**Context:** `app/tools/finance/alpha_vantage.py` stub exists. Do **not** ship in 2C.1. Add API keys to settings/`.env.example` only when implementing. Same DataSource port and per-source TTL/quota.

**Effort:** M  
**Priority:** P2  
**Depends on:** 2C.1; preferably after 2C.3

## Deferred beyond Phase 2C

### Portfolio / watchlist dashboard

**What:** Personalized surface to review held + watched tickers for buy/trim/add without per-ticker Yahoo grind.

**Why:** Product job-to-be-done beyond single-ticker ADK JSON; primary UX for dogfood reliability.

**Context:** Depends on richer FundamentalsSnapshot + multi-source spine. Run `/plan-design-review` before UI. Keep Phase0Result (or successor) as contract.

**Effort:** XL  
**Priority:** P2  
**Depends on:** Phase 2C core (2C.1–2C.3)

### Portfolio / correlation layer

**What:** Multi-ticker orchestration, concentration, and correlation-aware risk.

**Why:** Product is FolioTracker; Phase 0 is single-ticker only.

**Context:** `portfolio_agent` stub exists. Needs portfolio schemas, batch evidence, and risk services. Do not start until single-ticker spine + scoring + 2C fundamentals are trusted.

**Effort:** XL  
**Priority:** P2  
**Depends on:** Thin Phase 2 (done); preferably 2C richer fundamentals

### Cache / memory beyond Phase 0 TTL files

**What:** Richer ticker/company/session memory; optional shared cache.

**Why:** Cost control and continuity across research sessions.

**Context:** Phase 0 has local file TTL cache; 2C adds per-source files. Memory stubs under `app/memory/` stay untouched until needed.

**Effort:** M  
**Priority:** P3  
**Depends on:** Phase 0 cache proven; 2C per-source cache landed

## Phase 3 — Platform

### Custom API / UI beyond `adk web`

**What:** First-party HTTP API and/or minimal research UI.

**Why:** Real users won’t live in ADK’s default chat forever.

**Context:** Run `/plan-design-review` before building UI. Keep Phase0Result as the contract. Conflicts UI can render `evidence.conflicts`; scorecard can render `scorecard`.

**Effort:** L  
**Priority:** P3  
**Depends on:** Phase 0 product-complete; ideally 2C

### Observability backends (metrics, traces, alerts)

**What:** Export pipeline latency, cache hit rate, per-source error/rate-limit rates, Yahoo/thesis error rates.

**Why:** Local logs won’t scale past solo use.

**Context:** Phase 0 has structured logs + `request_id` only. 2C should log per-source hit/miss/skip.

**Effort:** M  
**Priority:** P3  
**Depends on:** Non-local deployment plans

### Production deploy + rollback runbooks

**What:** Hosted ADK/API deploy, env management, smoke checks.

**Why:** Local-only isn’t a product.

**Context:** Architecture deploy section is Phase 0 local-only by design. Redis multi-tenant rate-limit platform stays out until then.

**Effort:** L  
**Priority:** P3  
**Depends on:** Custom API or hosted ADK decision

## Completed

### Phase 2C.2 — Yahoo fundamentals enrichment (2026-07-25)

- Expanded `FinancialMetrics` / `FundamentalsSnapshot`: profile, returns (3M/1Y/YTD), revenue/earnings history, BS/CF summaries, trailing + forward P/E, EPS, ROE
- `yahoo_finance` fetches info + 1y history + quarterly statements (best-effort)
- Evidence serializes enrichment; scoring uses trailing→forward P/E and earnings_growth fallback
- Unit tests for parse/returns/statements; full unit suite green

### Phase 2C.1 — Provider port + per-source cache (2026-07-25)

- `DataSourceConfig` + registry (`yahoo`, `google_news`, `sec_edgar`)
- Per-source file cache under `.cache/foliotracker/sources/{source_id}/`
- Soft local rate budgets; stale serve when budget exhausted
- `phase0_pipeline` fan-out via `cached_fetch` (Yahoo still fatal; news/SEC → partial)
- Unit tests: registry, cache, fetch, settings; full unit suite green

### Phase 2C design lock — Approach B1 (2026-07-25)

- Office-hours design doc: provider port, per-source cache, Yahoo → SEC XBRL → AV
- Architecture Phase 2C section; PRD/TODOS/implementation-status updated
- Explicit non-goals: Kafka, Redis rate-limit platform, shipping all commercial APIs day-1

### Phase 2B — Scoring service (2026-07-24)

- `score_from_metrics`: `FinancialMetrics` → `Scorecard` (0–100 or null per dim)
- Optional `scorecard` on `Phase0Result`; pipeline step after evidence / before thesis
- Unit tests for clamps, null paths, dimension directions
- `scoring_agent` remains stubbed (service-only); `execution_score` always null in v1
- Clear `.cache/foliotracker/phase0/` after upgrade (schema bump)

### Phase 2A — SEC specialist (2026-07-24)

- `sec_edgar` tool (ticker→CIK→recent 10-K/10-Q/8-K metadata)
- `evidence_from_filings` + SEC cap + `material_event` conflict topic
- Pipeline fan-out Yahoo + news + SEC; SEC-only failure → `partial`

### Phase 1 — Evidence spine expansion (2026-07-24)

- Second specialist agent (Google News RSS) beside Yahoo
- Evidence aggregator merge + conflict model (`EvidenceConflict`, dedupe, news cap)
- Agent disagreement / adjudication UX as JSON `evidence.conflicts` (no custom UI)
