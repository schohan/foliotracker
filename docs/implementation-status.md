# Implementation Status

Tracks what exists vs. what is still scaffold-only, relative to [architecture.md](architecture.md).

**Active scope:** Thin Phase 2 — **SEC specialist (2A) done**; **scoring (2B) next**. Portfolio/memory deferred — see [TODOS.md](../TODOS.md).

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
| Shared schemas (`app/schemas/`) | Done | Phase 0/1 contracts; filings schemas in 2A |
| Evidence layer | Done | `evidence_from_metrics` + `evidence_from_news` + `evidence_from_filings` |
| Evidence aggregator | Done | Dedupe, news/SEC caps, `EvidenceConflict`, status rules |
| Configs (`settings`, `models`) | Done | TTL, cache dir, Yahoo/news/SEC timeouts + User-Agent |
| Memory layer | Todo | Stub classes only (deferred past Phase 2) |
| Cache runtime | Done | Local TTL file cache (`.cache/foliotracker/phase0/`) |
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
| Other domain stubs except report/thesis | Todo (out of Phase 0–2A) |

## Agents — report

| Module | Status |
|--------|--------|
| `thesis_agent` | Done | Gemini JSON thesis + 1 citation repair; `EmptyClaimsError` / structured `error_code` |
| `scoring_agent` | Todo | After scoring service (2B) |
| `report_agent` | Todo |

---

## Tools

| Category | Modules | Status |
|----------|---------|--------|
| Finance | `yahoo_finance` | Done (yfinance) |
| Finance | `alpha_vantage`, `finnhub`, `polygon` | Todo |
| News | `google_news` | Done (RSS) |
| News | `news_api` | Todo (stub) |
| Filings | `sec_edgar` | Done (2A metadata) |
| Filings | `sec_xbrl` | Todo (stub; deferred past 2A) |
| Search / web / social / ai / cache tools / persistence | — | Todo |

---

## Workflows

| Module | Status |
|--------|--------|
| All listed workflows | Todo (Phase 0 uses `phase0_pipeline` service instead) |

---

## Services

| Module | Status |
|--------|--------|
| `evidence` (`evidence_from_metrics`, `evidence_from_news`, `evidence_from_filings`, aggregator) | Done |
| `phase0_cache` | Done |
| `phase0_session` | Done |
| `phase0_pipeline` | Done (Yahoo + news + SEC fan-out) |
| `scoring` | Todo (2B) |
| `valuation` / `financial_math` / `ranking` / `normalization` | Todo |

---

## Schemas

| Module | Status | Notes |
|--------|--------|-------|
| `evidence` | Done | `id`, `BundleStatus`, conflicts |
| `phase0` | Done | `Phase0Result`, `Phase0ErrorCode`, disclaimer, cache_hit, request_id |
| `report` | Done | `ThesisClaim`, cited thesis |
| `ticker` | Done | `normalize_ticker` |
| `news` | Done | `NewsArticle`, `NewsBatch` |
| `filings` | Done (2A) | `SecFiling`, `SecFilingsBatch` |
| `financials` / others | Partial | Used by Phase 0 |

---

## Memory

| Module | Status |
|--------|--------|
| All | Todo (deferred past thin Phase 2) |

---

## Suggested next milestones

1. **2B:** scoring service (formulas + unit tests before any agent consumes scores)
2. Dogfood via `adk web` — analyze a ticker end-to-end with SEC evidence
3. Set a real `SEC_USER_AGENT` contact email before heavy live EDGAR use

---

## Changelog

| Date | Change |
|------|--------|
| 2026-07-24 | Phase 2A done: SEC EDGAR tool, filings evidence, pipeline fan-out |
| 2026-07-24 | Thin Phase 2 lock: SEC (2A) → scoring (2B); portfolio/memory deferred |
| 2026-07-14 | Initial scaffold: package layout, schema stubs, ADK root agent, this tracker |
| 2026-07-21 | CEO review: Phase 0 is active scope; link TODOS.md for deferred work |
| 2026-07-21 | Phase 0 contracts + unit tests + eval fixtures (impl still pending) |
| 2026-07-21 | Phase 0 implemented: yahoo, evidence, cache, thesis, pipeline, evals runner |
| 2026-07-24 | Phase 1 complete: Google News, aggregator conflicts, multi-evidence evals |
