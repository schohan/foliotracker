# Implementation Status

Tracks what exists vs. what is still scaffold-only, relative to [architecture.md](architecture.md).

**Active scope:** Phase 0 thin slice only (see architecture.md). Deferred work lives in [TODOS.md](../TODOS.md).

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
| Project config (`pyproject.toml`, `.env.example`) | Done | Includes yfinance + Phase 0 env vars |
| Shared schemas (`app/schemas/`) | Done | Phase 0 contracts wired |
| Evidence layer | Done | `evidence_from_metrics` + pass-through aggregate |
| Evidence aggregator | Done | Pass-through only (Phase 0) |
| Configs (`settings`, `models`) | Done | TTL, cache dir, Yahoo timeout |
| Memory layer | Todo | Stub classes only |
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
| `portfolio_agent` | Todo |
| `valuation_agent` | Todo |
| `app/agent.py` (Portfolio Research root) | Done |

## Agents — company / financials / market / technical / governance

| Area | Status |
|------|--------|
| All domain stubs except report/thesis | Todo (out of Phase 0) |

## Agents — report

| Module | Status |
|--------|--------|
| `thesis_agent` | Done | Gemini JSON thesis + 1 citation repair |
| `scoring_agent` | Todo |
| `report_agent` | Todo |

---

## Tools

| Category | Modules | Status |
|----------|---------|--------|
| Finance | `yahoo_finance` | Done (yfinance) |
| Finance | `alpha_vantage`, `finnhub`, `polygon` | Todo |
| Filings / search / web / news / social / ai / cache tools / persistence | — | Todo |

---

## Workflows

| Module | Status |
|--------|--------|
| All listed workflows | Todo (Phase 0 uses `phase0_pipeline` service instead) |

---

## Services

| Module | Status |
|--------|--------|
| `evidence` (`evidence_from_metrics`, `aggregate_evidence`) | Done |
| `phase0_cache` | Done |
| `phase0_session` | Done |
| `phase0_pipeline` | Done |
| `valuation` / `financial_math` / `scoring` / `ranking` / `normalization` | Todo |

---

## Schemas

| Module | Status | Notes |
|--------|--------|-------|
| `evidence` | Done | `id`, `BundleStatus` |
| `phase0` | Done | `Phase0Result`, disclaimer, cache_hit, request_id |
| `report` | Done | `ThesisClaim`, cited thesis |
| `ticker` | Done | `normalize_ticker` |
| `financials` / others | Partial | Used by Phase 0 |

---

## Memory

| Module | Status |
|--------|--------|
| All | Todo |

---

## Suggested next milestones

1. Run on-demand evals: `python -m evaluations.phase0.run` (needs `GOOGLE_API_KEY`)
2. Dogfood via `adk web` — analyze a ticker end-to-end
3. Phase 1 from TODOS.md (second specialist + real aggregator merge)

---

## Changelog

| Date | Change |
|------|--------|
| 2026-07-14 | Initial scaffold: package layout, schema stubs, ADK root agent, this tracker |
| 2026-07-21 | CEO review: Phase 0 is active scope; link TODOS.md for deferred work |
| 2026-07-21 | Phase 0 contracts + unit tests + eval fixtures (impl still pending) |
| 2026-07-21 | Phase 0 implemented: yahoo, evidence, cache, thesis, pipeline, evals runner |
