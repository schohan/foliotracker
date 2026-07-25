# TODOS

Deferred work from CEO plan review (2026-07-21) and eng/office-hours design (2026-07-25). Phase 1–2B shipped. Phase 2C Approach B1 **complete** (through AV forward fill-gaps). Next: portfolio/watchlist dashboard — see [docs/architecture.md](docs/architecture.md).

**Phase 2 lock (2026-07-24):** Thin Phase 2 = **SEC specialist → scoring service**. Portfolio and cache/memory deferred.

**Thin Phase 2 complete** = 2A + 2B (**both done 2026-07-24**).

**Phase 2C lock (2026-07-25):** Provider port + per-source cache; Yahoo enrich day-1; SEC XBRL; Alpha Vantage fill-gaps. No Kafka.

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

### Phase 2C — Alpha Vantage forward fill-gaps (2026-07-25)

- `alpha_vantage` OVERVIEW → `forward_pe` / market fill-nulls (soft-fail; key optional)
- Registry source `alpha_vantage` enabled only when `ALPHA_VANTAGE_API_KEY` set
- Merge trust: Yahoo > AV for market fields; SEC > Yahoo > AV for statements
- Pipeline fans out AV when keyed; AV failure never fatal
- `eps_forward` still Yahoo-only (not on OVERVIEW); min fundamentals set unchanged

### Phase 2C.3 — Soften Yahoo-fatal + SEC XBRL (2026-07-25)

- `sec_xbrl` companyfacts → `FinancialMetrics` (BS/CF/EPS/margins; no market P/E)
- `merge_fundamentals` fill-nulls by trust + `field_provenance` + field conflicts
- Pipeline fans out Yahoo + news + SEC filings + XBRL; Yahoo failure → `partial` iff `has_minimum_fundamentals(merged)`
- Min field checklist remains editable in `fundamentals_minimum.py`
- Min set trimmed: `pe_ratio` / `forward_pe` / `eps_forward` not required (SEC-only soften viable); may re-add when AV/FMP lands

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
