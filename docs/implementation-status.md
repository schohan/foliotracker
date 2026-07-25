# Implementation Status

Tracks what exists vs. what is still scaffold-only, relative to [architecture.md](architecture.md).

**Active scope:** Thin Phase 2 **complete**. Phase **2C.1–2C.2 done**. **Next:** 2C.3 soften Yahoo-fatal + SEC XBRL. See [TODOS.md](../TODOS.md).

**Legend**

| Status | Meaning |
|--------|---------|
| Done | Implemented and usable |
| Partial | Skeleton / contracts only |
| Todo | Not started (file may exist as stub) |

Update this file whenever a module moves from stub → working.

---

## Platform foundation

| Item | Status | Notes |
|------|--------|-------|
| Repository / package layout (`app/`) | Done | Matches architecture capability layout |
| ADK entrypoint (`app/`) | Done | `analyze_ticker` tool → Phase 0 pipeline |
| Project config (`pyproject.toml`, `.env.example`) | Done | Includes yfinance + Phase 0/1/2A env vars |
| Shared schemas (`app/schemas/`) | Done | Phase 0–2B contracts; optional `scorecard` on `Phase0Result` |
| Evidence layer | Done | `evidence_from_metrics` + `evidence_from_news` + `evidence_from_filings` |
| Evidence aggregator | Done | Dedupe, news/SEC caps, `EvidenceConflict`, status rules |
| Configs (`settings`, `models`) | Done | TTL, cache dir, Yahoo/news/SEC timeouts + User-Agent |
| Memory layer | Todo | Stub classes only (deferred past Phase 2) |
| Cache runtime | Done | Local TTL file cache (`.cache/foliotracker/phase0/`) — whole Phase0Result |
| Per-source cache / DataSource registry | Done (2C.1) | `source_registry`, `source_cache`, `cached_fetch`; wraps Yahoo/news/SEC |
| Fundamentals merge + provenance | Partial | Enriched Yahoo snapshot (2C.2); multi-source merge in 2C.3 |
| Evaluations framework | Done | Cases + rubric + `python -m evaluations.phase0.run` |
| Prompts library | Todo | Thesis prompt inline in thesis_agent |

---

## Agents — orchestrator

| Module | Status |
|--------|--------|
| `stock_research_agent` | Todo |
| `earnings_agent` | Todo |
| `screening_agent` | Todo |
| `portfolio_agent` | Todo (deferred past thin Phase 2) |
| `valuation_agent` | Todo |
| `app/agent.py` (Portfolio Research root) | Done |

## Agents — company / financials / market / technical / governance

| Area | Status |
|------|--------|
| `sec_agent` (governance) | Todo (logic lives in pipeline + `sec_edgar` tool for 2A) |
| Other domain stubs except report/thesis | Todo (out of Phase 0–2B) |

## Agents — report

| Module | Status |
|--------|--------|
| `thesis_agent` | Done | Gemini JSON thesis + 1 citation repair; `EmptyClaimsError` / structured `error_code` |
| `scoring_agent` | Todo | Intentionally stubbed — thin 2B ships `score_from_metrics` service only |
| `report_agent` | Todo |

---

## Tools

| Category | Modules | Status |
|----------|---------|--------|
| Finance | `yahoo_finance` | Done (2C.2) — profile, returns, BS/CF, trailing/forward P/E via `cached_fetch` |
| Finance | `alpha_vantage`, `finnhub`, `polygon` | Todo — after SEC XBRL (2C.3); same DataSource port |
| News | `google_news` | Done (RSS) — via `cached_fetch` (2C.1) |
| News | `news_api` | Todo (stub) |
| Filings | `sec_edgar` | Done (2A metadata) — via `cached_fetch` (2C.1) |
| Filings | `sec_xbrl` | Todo — Phase 2C.3 first secondary fundamentals provider |
| Search / web / social / ai / cache tools / persistence | — | Todo |

---

## Workflows

| Module | Status |
|--------|--------|
| All listed workflows | Todo (scaffold only — not Temporal; Phase 0/2C uses `phase0_pipeline` + provider port) |

Phase 2C does **not** introduce a separate workflow engine. Ingestion = on-demand provider fetches with per-source cache inside the research pipeline.

---

## Services

| Module | Status |
|--------|--------|
| `evidence` (`evidence_from_metrics`, `evidence_from_news`, `evidence_from_filings`, aggregator) | Done |
| `phase0_cache` | Done |
| `phase0_session` | Done (clears `scorecard`) |
| `phase0_pipeline` | Done — fan-out via per-source `cached_fetch` (2C.1) + scoring + thesis |
| `scoring` | Done (2B) — `score_from_metrics` (consumes merged snapshot in 2C.2+) |
| `source_registry` / `source_cache` / `source_fetch` | Done (2C.1) |
| `merge_fundamentals` | Todo (Phase 2C.3) |
| `valuation` / `financial_math` / `ranking` / `normalization` | Todo |

---

## Schemas

| Module | Status | Notes |
|--------|--------|-------|
| `evidence` | Done | `id`, `BundleStatus`, conflicts |
| `phase0` | Done | `Phase0Result` + optional `scorecard`, `Phase0ErrorCode`, disclaimer, cache_hit, request_id |
| `report` | Done | `ThesisClaim`, cited thesis; `Scorecard` (0–100 dims) |
| `ticker` | Done | `normalize_ticker` |
| `news` | Done | `NewsArticle`, `NewsBatch` |
| `filings` | Done (2A) | `SecFiling`, `SecFilingsBatch` |
| `financials` / others | Done (2C.2) | Enriched `FinancialMetrics` (= `FundamentalsSnapshot`); series + statement summaries |

---

## Memory

| Module | Status |
|--------|--------|
| All | Todo (deferred past thin Phase 2) |

---

## Suggested next milestones

1. Dogfood enriched fields via `adk web` — confirm forward P/E, returns, BS/CF in evidence JSON
2. Implement 2C.3 — soften Yahoo-fatal + `sec_xbrl`; then optional AV/FMP
3. Set a real `SEC_USER_AGENT` contact email before heavy live EDGAR/XBRL use

---

## Changelog

| Date | Change |
|------|--------|
| 2026-07-25 | Phase 2C.2 done: enriched FinancialMetrics, Yahoo profile/returns/statements, scoring/evidence wire-up |
| 2026-07-25 | Phase 2C.1 done: DataSource registry, per-source cache, soft rate budgets, pipeline wire-up |
| 2026-07-25 | Phase 2C designed (B1): provider port, per-source cache, Yahoo → SEC XBRL → AV; status rows added |
| 2026-07-24 | Phase 2B done: `score_from_metrics`, `Phase0Result.scorecard`, pipeline + session wire-up |
| 2026-07-24 | Lock 2B scoring contract in docs; expand next milestones (schemas → tests → service → pipeline) |
| 2026-07-24 | Phase 2A done: SEC EDGAR tool, filings evidence, pipeline fan-out |
| 2026-07-24 | Thin Phase 2 lock: SEC (2A) → scoring (2B); portfolio/memory deferred |
| 2026-07-14 | Initial scaffold: package layout, schema stubs, ADK root agent, this tracker |
| 2026-07-21 | CEO review: Phase 0 is active scope; link TODOS.md for deferred work |
| 2026-07-21 | Phase 0 contracts + unit tests + eval fixtures (impl still pending) |
| 2026-07-21 | Phase 0 implemented: yahoo, evidence, cache, thesis, pipeline, evals runner |
| 2026-07-24 | Phase 1 complete: Google News, aggregator conflicts, multi-evidence evals |
