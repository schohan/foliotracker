# TODOS

Deferred work from CEO plan review (2026-07-21). Phase 1 evidence spine (news + aggregator conflicts) is implemented — see [docs/architecture.md](docs/architecture.md).

**Phase 2 lock (2026-07-24):** Thin Phase 2 = **SEC specialist → scoring service**. Portfolio and cache/memory deferred to later.

## Phase 2 — Product depth (in progress)

### SEC specialist agent — **DONE (2A, 2026-07-24)**

**What:** Add SEC filings specialist beside Yahoo + news.

**Why:** Completes multi-domain research with primary filings evidence.

**Context:** EDGAR metadata tool + `evidence_from_filings` wired into pipeline fan-out and aggregator (`material_event` conflict). `sec_xbrl` remains stubbed.

**Effort:** L  
**Priority:** P2  
**Depends on:** Phase 1 aggregator + conflict model  
**Status:** Done

### Scoring service (Growth / Value / Moat / Risk / …) — **NEXT (2B)**

**What:** Deterministic scoring from evidence/metrics; never LLM arithmetic.

**Why:** Reusable scores for screening, ranking, and reports.

**Context:** Names exist in deferred architecture and stub packages. Define formulas + ranges + unit tests before any agent consumes scores.

**Effort:** M  
**Priority:** P2  
**Depends on:** Phase 0 financial evidence path stable; prefer after SEC so scores can later cite filings

## Deferred beyond Phase 2

### Portfolio / correlation layer

**What:** Multi-ticker orchestration, concentration, and correlation-aware risk.

**Why:** Product is FolioTracker; Phase 0 is single-ticker only.

**Context:** `portfolio_agent` stub exists. Needs portfolio schemas, batch evidence, and risk services. Do not start until single-ticker spine + scoring are trusted.

**Effort:** XL  
**Priority:** P2  
**Depends on:** Thin Phase 2 (SEC + scoring)

### Cache / memory beyond Phase 0 TTL files

**What:** Richer ticker/company/session memory; optional shared cache.

**Why:** Cost control and continuity across research sessions.

**Context:** Phase 0 has local file TTL cache only. Memory stubs under `app/memory/` stay untouched until needed.

**Effort:** M  
**Priority:** P3  
**Depends on:** Phase 0 cache proven in use

## Phase 3 — Platform

### Custom API / UI beyond `adk web`

**What:** First-party HTTP API and/or minimal research UI.

**Why:** Real users won’t live in ADK’s default chat forever.

**Context:** Run `/plan-design-review` before building UI. Keep Phase0Result as the contract. Conflicts UI can render `evidence.conflicts`.

**Effort:** L  
**Priority:** P3  
**Depends on:** Phase 0 product-complete

### Observability backends (metrics, traces, alerts)

**What:** Export pipeline latency, cache hit rate, Yahoo/thesis error rates.

**Why:** Local logs won’t scale past solo use.

**Context:** Phase 0 has structured logs + `request_id` only.

**Effort:** M  
**Priority:** P3  
**Depends on:** Non-local deployment plans

### Production deploy + rollback runbooks

**What:** Hosted ADK/API deploy, env management, smoke checks.

**Why:** Local-only isn’t a product.

**Context:** Architecture deploy section is Phase 0 local-only by design.

**Effort:** L  
**Priority:** P3  
**Depends on:** Custom API or hosted ADK decision

## Completed

### Phase 2A — SEC specialist (2026-07-24)

- `sec_edgar` tool (ticker→CIK→recent 10-K/10-Q/8-K metadata)
- `evidence_from_filings` + SEC cap + `material_event` conflict topic
- Pipeline fan-out Yahoo + news + SEC; SEC-only failure → `partial`

### Phase 1 — Evidence spine expansion (2026-07-24)

- Second specialist agent (Google News RSS) beside Yahoo
- Evidence aggregator merge + conflict model (`EvidenceConflict`, dedupe, news cap)
- Agent disagreement / adjudication UX as JSON `evidence.conflicts` (no custom UI)
