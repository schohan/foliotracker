# TODOS

Deferred work from CEO plan review (2026-07-21). Phase 0 thin slice is active — see [docs/architecture.md](docs/architecture.md). Do not pull these into Phase 0 without an explicit scope decision.

## Phase 1 — Evidence spine expansion

### Second specialist agent (news or SEC)

**What:** Add one non-financial specialist and fan-out beside the Yahoo financial path.

**Why:** Proves multi-domain research; forces real aggregation instead of pass-through.

**Context:** Phase 0 has a single evidence source. Pick news *or* SEC first (not both). Wire via ADK ParallelAgent or sequential join into the aggregator. Update evals for multi-evidence citation.

**Effort:** L  
**Priority:** P1  
**Depends on:** Phase 0 shipped (cited thesis path + evals green)

### Evidence aggregator merge + conflict model

**What:** Replace pass-through aggregator with dedupe, conflict records, and multi-item bundles.

**Why:** Specialists will disagree; silent overwrite is a product bug.

**Context:** Architecture names a “evidence graph” but Phase 0 is a flat list. Define merge keys, conflict schema, and thesis rules when evidence disagrees. Keep aggregator as a service (no LLM).

**Effort:** L  
**Priority:** P1  
**Depends on:** Second specialist agent

### Agent disagreement / adjudication UX

**What:** Surface conflicting specialist conclusions to the user (or a human PM) instead of averaging them away.

**Why:** FundaPod-style independence beats false consensus for investment research.

**Context:** Not Phase 0. Requires conflict model first. Could be JSON conflict list before any UI.

**Effort:** M  
**Priority:** P2  
**Depends on:** Evidence aggregator merge + conflict model

## Phase 2 — Product depth

### Scoring service (Growth / Value / Moat / Risk / …)

**What:** Deterministic scoring from evidence/metrics; never LLM arithmetic.

**Why:** Reusable scores for screening, ranking, and reports.

**Context:** Names exist in deferred architecture and stub packages. Define formulas + ranges + unit tests before any agent consumes scores.

**Effort:** M  
**Priority:** P2  
**Depends on:** Phase 0 financial evidence path stable

### Portfolio / correlation layer

**What:** Multi-ticker orchestration, concentration, and correlation-aware risk.

**Why:** Product is FolioTracker; Phase 0 is single-ticker only.

**Context:** `portfolio_agent` stub exists. Needs portfolio schemas, batch evidence, and risk services. Do not start until single-ticker spine is trusted.

**Effort:** XL  
**Priority:** P2  
**Depends on:** Phase 0 + preferably scoring

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

**Context:** Run `/plan-design-review` before building UI. Keep Phase0Result as the contract.

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

_(none yet)_
