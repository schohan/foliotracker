# FolioTracker Product Requirements Document (PRD)

**Product:** FolioTracker — AI portfolio and stock research on [Google ADK](https://adk.dev/)  
**Status:** Thin Phase 2 **complete** (2A SEC + 2B scoring); Phase 2C multi-source ingestion **designed** (B1) — impl slices pending  
**Audience:** Executives (vision, roadmap, risk) and engineers (contracts, acceptance criteria, phase boundaries)  
**Last updated:** 2026-07-25

**Related:** [architecture.md](architecture.md) · [implementation-status.md](implementation-status.md) · [TODOS.md](../TODOS.md)

---

## Table of contents

1. [Overview](#1-overview)
2. [Problem and opportunity](#2-problem-and-opportunity)
3. [Goals and non-goals](#3-goals-and-non-goals)
4. [Personas and primary jobs](#4-personas-and-primary-jobs)
5. [User features](#5-user-features)
6. [System features](#6-system-features)
7. [Core user journey](#7-core-user-journey)
8. [Success metrics](#8-success-metrics)
9. [Product principles](#9-product-principles)
10. [Roadmap](#10-roadmap)
11. [Constraints and compliance](#11-constraints-and-compliance)
12. [Open questions](#12-open-questions)
13. [Related docs](#13-related-docs)

---

## 1. Overview

FolioTracker turns a ticker symbol into **structured, citable research**: an evidence bundle grounded in live market and news sources, plus an investment thesis where every material claim cites evidence IDs. The product is deliberately **evidence-first** — LLMs reason over structured findings; they do not invent numbers or hide missing data.

Today the product ships locally via `adk web` / `adk run app`. The user asks to analyze a ticker (for example, `Analyze NVDA`); the system returns a `Phase0Result` JSON payload with status, evidence (including conflicts when sources disagree), a cited thesis when possible, a fixed non-advice disclaimer, cache metadata, and a request id for log correlation.

**What exists now (Phase 0–2B):** single-ticker research from Yahoo Finance metrics, Google News RSS headlines, and SEC EDGAR filing metadata, merged by a deterministic evidence aggregator, with disagreement surfaced as `evidence.conflicts`, plus a deterministic `scorecard` on `Phase0Result`. Cache is a single whole-result TTL; Yahoo failure is fatal for the pipeline.

**What comes next (Phase 2C):** multi-provider-ready fundamentals — provider port, per-source TTL/quota, field provenance, Yahoo enrichment day-1, then SEC XBRL for statements, then commercial APIs (e.g. Alpha Vantage) for forward-estimate gaps. Personalized portfolio/watchlist dashboard and Phase 3 platform work follow. See [Roadmap](#10-roadmap) and [TODOS.md](../TODOS.md).

How the system is built lives in [architecture.md](architecture.md). What is implemented vs stub lives in [implementation-status.md](implementation-status.md). Deferred work lives in [TODOS.md](../TODOS.md).

---

## 2. Problem and opportunity

### Problem

Equity research for individuals and small teams is fragmented across terminals, filings sites, news feeds, and chatbots. Generative AI makes narrative research cheap, but most chatbot answers are **unverifiable**: numbers may be hallucinated, sources are opaque, and partial data failures are silent. There is no shared **evidence contract** that downstream analysis, scoring, and portfolio tools can reuse.

### Opportunity

FolioTracker owns the load-bearing spine: **fetch → evidence → cite → score / portfolio**. Once that spine is trusted, specialists (news, SEC, technicals), scorecards, and multi-ticker risk become composition over the same contracts — not one-off prompts.

### Product bet

Users will prefer a labeled, citable, sometimes-partial result over a fluent but ungrounded essay. Trust compounds when every claim points at evidence and disagreements are visible.

---

## 3. Goals and non-goals

### Goals

| Goal | Why it matters |
|------|----------------|
| Cite-first research | Material claims must reference evidence IDs present in the bundle |
| Honest degradation | Missing or conflicting data → `partial` / `error`, never a silent fake thesis |
| Deterministic calc layer | Scores, math, and conflict detection are services — never LLM arithmetic |
| Eval-first delivery | Unit tests and LLM eval fixtures gate each phase before shipping reasoning changes |
| Reusable spine | New specialists and portfolio features plug into evidence + schemas |

### Non-goals (current product)

| Non-goal | Clarification |
|----------|---------------|
| Investment advice | Output is informational/educational only; fixed disclaimer always present |
| Brokerage / order execution | No trading, accounts, or order routing |
| Full research terminal | No custom UI yet; delivery is ADK chat + JSON |
| Production multi-tenant SaaS | Local process + file cache only until Phase 3 |
| Web scraping of article bodies | Phase 1 news is RSS headlines + URLs only |
| Pretending stubs are live | Scaffold agents/tools stay marked Todo until implemented |

---

## 4. Personas and primary jobs

| Persona | Primary job | Current surface |
|---------|-------------|-----------------|
| Individual investor / power user | “Give me a grounded take on this ticker I can verify” | `adk web` chat → JSON result |
| Research analyst (dogfood) | Stress citation quality, conflicts, and partial paths | Chat + unit tests + on-demand evals |
| Portfolio manager (future) | Multi-ticker concentration and correlation-aware risk | Deferred past thin Phase 2 |
| Platform engineer (future) | Host API/UI, observe latency and error rates | Planned Phase 3 |

**Primary job-to-be-done (now):** Given one ticker, return evidence + cited thesis I can trust enough to continue my own research.

**Primary job-to-be-done (2C / dogfood):** Decide buy / hold / trim / add without a long Yahoo click-tour — richer fundamentals (returns, earnings/revenue trends, BS/CF, forward metrics) with honest gaps when a source fails.

**Secondary job-to-be-done (near-term):** See when financial metrics and headlines disagree without reading raw tool dumps.

**Future job-to-be-done:** Personalized dashboard across portfolio + watchlist; score and compare names; portfolio-level risk from the same evidence spine.

---

## 5. User features

Capabilities the human experiences. Separate from [system features](#6-system-features).

### 5.1 Shipped (Phase 0–2B)

| Feature | What the user gets | Acceptance notes |
|---------|--------------------|------------------|
| Single-ticker analysis | Ask e.g. `Analyze NVDA`; receive structured research | Ticker validated before tools run |
| Structured research payload | Status, evidence bundle, thesis (when available), scorecard (when scorable), error message when failed | Contract: `Phase0Result` |
| Cited thesis | Summary + material claims each citing evidence IDs | Ships only with ≥1 material claim citing bundle evidence IDs; empty claims or uncited/dangling citations after one repair → fail closed (`status=error`); evidence may still be returned |
| Source disagreement | Conflicts listed under `evidence.conflicts` | JSON-first; no custom conflicts UI yet |
| Filings-aware research | SEC filing metadata in the same result as metrics + news | EDGAR metadata only (form, dates, accession, index URL); no full-document scrape |
| Deterministic scorecard | Growth / Value / Profitability / Moat / Risk scores (0–100 or null) | Pure Python from Yahoo metrics; `execution_score` null in v1; never LLM arithmetic |
| Fast repeat lookup | Same ticker within TTL returns prior result quickly | `cache_hit=true`; new `request_id` per serve |
| Always-on disclaimer | Non-advice copy on every response including errors | Fixed string; not optional |
| Honest status labels | `ok` / `partial` / `error` | Partial on gaps/conflicts; error when research cannot ship; thesis-stage failures use stable `error_code` |

### 5.2 Planned (Phase 2C + deferred)

| Feature | What the user gets | Phase | Status |
|---------|--------------------|-------|--------|
| Richer fundamentals | Forward P/E, returns, earnings/revenue series, BS/CF summaries in research | 2C | Designed — Yahoo enrich then SEC XBRL |
| Resilient multi-source data | Research continues with honest `partial` when one provider fails | 2C | Designed — provider port + merge |
| Independent source freshness | Each source refreshes on its own cadence (not one blob TTL) | 2C | Designed — per-source cache |
| Portfolio / watchlist dashboard | Fast buy/trim/add read across held + watched names | — | Deferred (depends on 2C) |
| Portfolio risk view | Multi-ticker concentration and correlation-aware risk | — | Deferred past thin Phase 2 (XL) |
| Session continuity | Richer memory across research sessions | — | Deferred past thin Phase 2 (P3) |
| First-party research UI / API | Use FolioTracker without living in ADK chat | 3 | Planned |
| Hosted product | Deployed service with runbooks and smoke checks | 3 | Planned |

Planned items are sequenced in [TODOS.md](../TODOS.md); 2C contracts are locked in [architecture.md](architecture.md).

---

## 6. System features

Platform capabilities engineers build behind the user experience. Separate from [user features](#5-user-features).

### 6.1 Shipped (Phase 0–2B)

| Feature | Role | Contract / location |
|---------|------|---------------------|
| Yahoo Finance tool | Fetch financial metrics (no LLM) | `app/tools/finance/yahoo_finance.py` → `FinancialMetrics` |
| Google News RSS tool | Fetch headlines + URLs (no API key, no LLM) | `app/tools/news/google_news.py` → `NewsBatch` |
| SEC EDGAR tool | Fetch recent filing metadata (User-Agent required; no LLM) | `app/tools/filings/sec_edgar.py` → `SecFilingsBatch` |
| Evidence from metrics | Pure Python: metrics → `Evidence` (`type=financial`, confidence `0.95`) | `evidence_from_metrics` |
| Evidence from news | Pure Python: articles → `Evidence` (`type=news`, confidence `0.7`) | `evidence_from_news` |
| Evidence from filings | Pure Python: filings → `Evidence` (`type=sec`, confidence `0.9`) | `evidence_from_filings` |
| Evidence aggregator | Dedupe, news/SEC caps, `EvidenceConflict`, bundle status rules | `aggregate_evidence` |
| Scoring service | Pure Python: metrics → `Scorecard` (0–100 or null per dim) | `score_from_metrics` |
| Pipeline fan-out | Yahoo + news + SEC via thread pool; news- or SEC-only failure → `partial`; score before thesis | `phase0_pipeline` |
| Thesis agent | Sole LLM step; optional bull/bear/risks/conviction; one citation repair | `thesis_agent` |
| Local TTL cache | File-backed `Phase0Result` cache (`ok`/`partial` only) | `.cache/foliotracker/phase0/` |
| Session clear (5A) | New ticker clears prior evidence/scorecard/thesis session keys | `phase0_session` |
| Schema invariants | Claim `evidence_ids` ⊆ bundle item ids when status ok/partial | `Phase0Result`, `InvestmentThesis` |
| CI unit tests | Default `pytest tests/unit` | No LLM required |
| On-demand LLM evals | Groundedness / citation fixtures | `python -m evaluations.phase0.run` |

**Output contract engineers must preserve** (`Phase0Result`):

- Always set: `ticker`, `status`, `disclaimer`, `cache_hit`, `request_id`
- On `ok`/`partial`: evidence bundle present; every claim citation resolves to an evidence id; thesis has ≥1 material claim
- Optional `scorecard: Scorecard | null` — null when no scorable metrics; null dims ok; never invent scores
- On `error`: set user-readable `error_message` and stable `error_code` (e.g. `THESIS_EMPTY_CLAIMS`); thesis-stage failures may still include `evidence` and `scorecard`
- Never cache `status=error`
- On cache hit: serve prior payload with `cache_hit=true` and a **new** `request_id`

**Source trust ladder (today):**

| Source | Confidence | Notes |
|--------|------------|-------|
| Yahoo Finance metrics | `0.95` | Primary financial source today (also feeds scores); enrich in 2C |
| SEC EDGAR filing metadata | `0.9` | Primary filings; metadata only in 2A |
| SEC XBRL statement facts | `0.95` planned | 2C slice 3 — preferred for BS/CF truth |
| Google News RSS | `0.7` | Headlines + URLs only |
| Alpha Vantage / FMP | TBD | After SEC XBRL — forward estimates / gap fill |

### 6.2 Planned (Phase 2C + deferred / Phase 3)

| Feature | Role | Phase | Status |
|---------|------|-------|--------|
| DataSource registry | `source_id`, trust, TTL, local rate budget, timeout, enabled | 2C | Designed |
| Per-source cache | File cache ticker × source; independent refresh | 2C | Designed |
| FundamentalsSnapshot + merge | Field provenance; fill-nulls by trust; conflicts on disagreement | 2C | Designed |
| Yahoo fundamentals enrichment | Statements/trends/forward where yfinance allows | 2C slice 2 | Todo |
| XBRL fact extraction | `sec_xbrl` structured BS/CF/EPS (no LLM in tools) | 2C slice 3 | Todo (after port) |
| Soften Yahoo-fatal | Yahoo down → `partial` when merge has enough | 2C slice 3 | Todo |
| Alpha Vantage / FMP | Forward estimates / gap fill after SEC XBRL | Later | Todo |
| Portfolio schemas + risk services | Batch evidence, concentration, correlation | — | Deferred past thin Phase 2 |
| Memory beyond TTL files | Ticker / company / session / portfolio memory | — | Deferred past thin Phase 2 (P3) |
| Observability backends | Metrics, traces, alerts beyond local logs | 3 | Planned |
| Production deploy + runbooks | Hosted ADK/API, env, smoke, rollback | 3 | Planned |

**Engineering invariant for scoring:** formulas and ranges land with unit tests **before** any agent consumes scores. LLMs must not perform score arithmetic. Thin 2B is **service-only** (`score_from_metrics`); `scoring_agent` stays stubbed.

**2B v1 dimensions (shipped):** scale `0.0–100.0` or `null` — see [architecture.md](architecture.md) clamp anchors.

---

## 7. Core user journey

```mermaid
flowchart TD
  userAsk["User: Analyze NVDA"]
  root["portfolio_research_agent"]
  validate["Validate ticker + clear session"]
  cache{"Local TTL cache hit?"}
  fetch["Yahoo + news + SEC fan-out"]
  evidence["Evidence builders + aggregator"]
  score["score_from_metrics"]
  thesis["thesis_agent citation repair"]
  result["Phase0Result JSON"]
  cached["Cached Phase0Result cache_hit true"]

  userAsk --> root --> validate --> cache
  cache -->|hit| cached --> result
  cache -->|miss| fetch --> evidence --> score --> thesis --> result
```

**Happy path:** metrics + news + SEC → evidence (optional conflicts) → scorecard → cited thesis → `status=ok` or `partial` → cache write.

**Shadow paths users must still understand:**

| Path | What’s missing / why | User-visible outcome |
|------|----------------------|----------------------|
| Blank / invalid ticker | Input invalid before tools | Reject / `status=error`, `error_code=INVALID_TICKER` |
| Ticker not found / Yahoo failure | Upstream financial data unavailable | `status=error`, `error_code=DATA_FETCH_FAILED`, no usable evidence |
| Empty metrics / evidence | Nothing to cite | `status=error`, `error_code=EMPTY_EVIDENCE` |
| News fails, Yahoo ok | News gap only | Financial (+ SEC) bundle, often `partial` |
| SEC fails, Yahoo ok | Filings gap only | Metrics (+ news) bundle, often `partial` |
| Conflicts detected | Sources disagree | Conflicts in evidence; typically `partial` |
| Thesis empty claims after repair | Model returned no material claims; evidence data may be fine | `status=error`, `error_code=THESIS_EMPTY_CLAIMS`, thesis null, evidence often present |
| Thesis uncited / dangling after repair | Claims lack valid evidence ids | `status=error`, `error_code=THESIS_UNCITED` or `THESIS_DANGLING_CITATION`, thesis null, evidence often present |
| Thesis generation failed | LLM empty/unusable output | `status=error`, `error_code=THESIS_GENERATION_FAILED`, thesis null, evidence often present |
| Repeat within TTL | — | Fast return, `cache_hit=true` |

---

## 8. Success metrics

| Metric | Target / signal | Audience |
|--------|-----------------|----------|
| Citation groundedness | Eval cases: claims cite only fixture evidence IDs; no invented numbers | Eng + product quality |
| Citation coverage | Material claims have ≥1 evidence id; dangling ids = fail | Eng |
| Thesis-stage labeling | Thesis failures use stable `error_code`; user `error_message` distinguishes data vs thesis failure | Eng + product |
| Honest labeling | Empty/missing data never returns a confident fake thesis | Exec trust |
| Conflict visibility | Disagreements appear in `evidence.conflicts` when heuristics fire | Product |
| Cache effectiveness | Repeat ticker within TTL → `cache_hit=true`; live path collapsed | Cost / UX |
| Latency (order of magnitude) | Cache hit &lt;50ms; live path dominated by Yahoo + thesis (seconds–tens of seconds) | Eng |
| Partial vs silent failure | Tool/news gaps → `partial` or `error` with message | Exec + eng |
| Unit CI green | `pytest tests/unit` is the default gate | Eng |

LLM evals remain **on-demand** (need `GOOGLE_API_KEY`); they are not the default CI gate.

---

## 9. Product principles

These are non-negotiable product and engineering rules (see also architecture):

1. **Agents reason; tools fetch; services calculate.** Agents must not perform HTTP or arithmetic.
2. **Schemas are the contracts.** Free-form agent prose is not the system of record.
3. **Evidence over vibes.** Downstream steps consume `Evidence`, not upstream chat text.
4. **Eval-first.** Tests and eval fixtures are reviewed before phase implementation code.
5. **Partial failure is visible.** Missing data yields a degraded, labeled result — never a silent fake thesis.

---

## 10. Roadmap

Phased delivery. Shipped phases are product fact; later phases are planned until sequenced in TODOS.

| Phase | Theme | User outcome | System outcome | Status |
|-------|-------|--------------|----------------|--------|
| **0** | Thin vertical slice | Single-ticker cited thesis from financials | Yahoo → evidence → thesis → TTL cache | **Shipped** |
| **1** | Evidence spine expansion | News context + visible source conflicts | News tool, merge aggregator, conflicts on result | **Shipped** (2026-07-24) |
| **2** | Product depth (thin) | Filings context + scorecards | SEC specialist → scoring service | **Complete** (2A+2B) |
| **2C** | Multi-source ingestion | Richer, resilient fundamentals | Provider port, per-source cache, Yahoo → SEC XBRL → AV | **Designed** (2026-07-25) |
| **3** | Platform | First-party UI/API, hosted product | Observability, deploy/rollback runbooks | **Planned** |

### Phase 2 sequence (locked 2026-07-24)

| Order | Item | Effort | Status |
|-------|------|--------|--------|
| **2A** | SEC specialist agent (EDGAR metadata) | L | **Done** (2026-07-24) |
| **2B** | Scoring service (Growth / Value / Moat / Risk / …) | M | **Done** (2026-07-24) |

### Phase 2C sequence (locked 2026-07-25 — Approach B1)

| Order | Item | Effort | Status |
|-------|------|--------|--------|
| Docs | Architecture / PRD / TODOS contracts | S | **Done** (2026-07-25) |
| **2C.1** | Source registry + per-source cache; wrap Yahoo/news/SEC | M | Todo |
| **2C.2** | Yahoo fundamentals enrichment + richer schemas | M | Todo |
| **2C.3** | Soften Yahoo-fatal + SEC XBRL fundamentals provider | L | Todo |
| Later | Alpha Vantage / FMP; portfolio/watchlist dashboard | L–XL | Todo |

**Deferred past 2C core:** portfolio / correlation (XL), cache / memory (P3), Kafka ingestion, Redis rate-limit platform.

### Phase 3 backlog (planned)

- Custom HTTP API and/or minimal research UI (design review before UI)
- Observability backends (metrics, traces, alerts)
- Production deploy + rollback runbooks

North-star (12-month ideal): full evidence graph, portfolio risk, scoring, and memory — composed on the same spine. FolioTracker does not pretend that cathedral is built today.

---

## 11. Constraints and compliance

| Constraint | Detail |
|------------|--------|
| Not advice | Fixed disclaimer on every `Phase0Result`: *“FolioTracker output is for informational and educational purposes only. It is not investment, legal, or tax advice. Do your own research.”* |
| Local-only deploy (now) | `adk web` / `adk run app`; no cloud multi-tenant product yet |
| Secrets | `GOOGLE_API_KEY` (and related) only in `.env`; never logged |
| Ticker validation | Strict pattern before tool calls or prompt inclusion |
| News surface | RSS headlines + URLs only (limits prompt-injection from scraped bodies) |
| SEC surface | EDGAR filing metadata only (no full filing HTML scrape in 2A) |
| Cache hygiene | Never cache errors; clear `.cache/foliotracker/phase0/` after breaking schema upgrades if needed (incl. 2B `scorecard`) |
| Stub honesty | Unimplemented agents/tools remain stubs until a phase lands them |

---

## 12. Open questions

### Resolved (2026-07-24)

1. **Phase 2 in-scope set** → Thin Phase 2: SEC + scoring only; portfolio + memory deferred.
2. **Order** → **SEC → scoring** (2A then 2B).
3. **Scoring dimensions v1** → Growth / Value / Profitability / Risk from Yahoo metrics; Moat = provisional gross-margin proxy; Execution = `null` in v1; scale `0–100` or `null`. Service-only (`score_from_metrics`); optional `scorecard` on `Phase0Result`. See [architecture.md](architecture.md) and [TODOS.md](../TODOS.md).

### Resolved (2026-07-25)

4. **Multi-source ingestion shape** → Approach B1: provider port + per-source cache; Yahoo enrich day-1; SEC XBRL next; Alpha Vantage later. No Kafka. See [architecture.md](architecture.md) Phase 2C.

### Still open

1. **Portfolio timing** — Start only after 2C richer fundamentals are trusted (recommended), or earlier thin multi-ticker batch?
2. **Minimum fundamentals set** — Which fields must be present before Yahoo-fatal can soften to `partial`? (Founder assignment: checklist from 3 watchlist tickers.)

---

## 13. Related docs

| Doc | Purpose |
|-----|---------|
| [architecture.md](architecture.md) | How the system is designed (flows, schemas, failures, ADK mapping) |
| [implementation-status.md](implementation-status.md) | What is Done / Partial / Todo vs architecture |
| [TODOS.md](../TODOS.md) | Deferred Phase 2+ work items |
| [evaluations/phase0/README.md](../evaluations/phase0/README.md) | How to run on-demand LLM evals |
| [README.md](../README.md) | Setup, run, and design principles |

---

## Changelog

| Date | Change |
|------|--------|
| 2026-07-24 | Phase 2B shipped (scorecard on Phase0Result); thin Phase 2 complete |
| 2026-07-24 | Lock 2B scoring dimensions; mark SEC/filings shipped (2A); resolve scoring open question |
| 2026-07-24 | Phase 2A shipped (SEC EDGAR); 2B scoring remains next |
| 2026-07-24 | Lock thin Phase 2: SEC (2A) → scoring (2B); resolve open sequencing questions |
| 2026-07-24 | Initial PRD: TOC, user vs system features, Phase 0/1 shipped, Phase 2/3 planned, open sequencing questions |
