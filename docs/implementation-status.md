# Implementation Status

Tracks what exists vs. what is still scaffold-only, relative to [architecture.md](architecture.md).

**Active scope:** Thin Phase 2 + **2C done**. Watchlist + Risk v2 **shipped**. **Daily Decision Brief Slice 1 shipped**. **Flexible ticker intake shipped**. **Next:** Brief dogfood Assignment, or Phase 3 evidence deepen. See [TODOS.md](../TODOS.md).

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
| Fundamentals merge + provenance | Done (2C.3) | `merge_fundamentals` + `field_provenance` + field conflicts |
| Min fundamentals checklist (`fundamentals_minimum`) | Done | Editable `MINIMUM_FUNDAMENTALS_FIELD_PATHS`; gate for soften Yahoo-fatal |
| Evaluations framework | Done | Cases + rubric + `python -m evaluations.phase0.run` |
| Prompts library | Todo | Thesis prompt inline in thesis_agent |
| Watchlist HTTP API (`app/api`) | Done | FastAPI: membership, refresh, research GET, risk, brief |
| Watchlist store / service | Done | Local JSON + `Phase0Result` → summary |
| Watchlist UI (`web/`) | Done | Svelte 5 dashboard (held/watched, detail panel, flexible intake) |
| Ticker intake service / API / UI | Done | `ticker_intake` + `POST /api/watchlist/intake` + `TickerIntakePanel` |
| Portfolio risk service | Done (v2) | Held equal-weight concentration + pairwise corr from Yahoo source-cache history |
| Risk UI (`RiskPage` + `PrimaryNav`) | Done (v2) | `Watchlist \| Risk \| Brief`; sector + names + top correlations tables |
| Brief service / store / classify | Done (Slice 1) | Gate/rank Generate; ring-14 + miss log; no Phase0 research |
| Brief UI (`BriefPage`) | Done (Slice 1) | Generate today, ranked rows, miss log |

---

## Agents — orchestrator

| Module | Status |
|--------|--------|
| `stock_research_agent` | Todo |
| `earnings_agent` | Todo |
| `screening_agent` | Todo |
| `portfolio_agent` | Todo (Risk v1 uses API/service; ADK agent still stub) |
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
| Finance | `alpha_vantage` | Done — OVERVIEW forward/market fill-gaps via `cached_fetch` (key optional) |
| Finance | `finnhub`, `polygon` | Todo (stubs) |
| News | `google_news` | Done (RSS) — via `cached_fetch` (2C.1) |
| News | `news_api` | Todo (stub) |
| Filings | `sec_edgar` | Done (2A metadata) — via `cached_fetch` (2C.1) |
| Filings | `sec_xbrl` | Done (2C.3) — companyfacts → BS/CF/EPS/margins via `cached_fetch` |
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
| `phase0_pipeline` | Done — Yahoo/news/SEC/XBRL/AV fan-out, merge, soften Yahoo-fatal, score, thesis |
| `scoring` | Done (2B) — `score_from_metrics` (consumes merged snapshot) |
| `portfolio_risk_service` | Done (v2) — Held concentration + top pairwise correlations |
| `yahoo_history` | Done — shared history parse + last-session daily % + move_score |
| `brief_classify` / `brief_store` / `brief_service` | Done (Slice 1) |
| `source_registry` / `source_cache` / `source_fetch` | Done (2C.1; registry includes `sec_xbrl`, `alpha_vantage`; `force_refresh`) |
| `merge_fundamentals` | Done (2C.3) |
| `valuation` / `financial_math` / `ranking` / `normalization` | Todo |

---

## Schemas

| Module | Status | Notes |
|--------|--------|-------|
| `evidence` | Done | `id`, `BundleStatus`, conflicts |
| `phase0` | Done | `Phase0Result` + optional `scorecard` + `fundamentals`, error codes, disclaimer, cache_hit, request_id |
| `report` | Done | `ThesisClaim`, cited thesis; `Scorecard` (0–100 dims) |
| `ticker` | Done | `normalize_ticker` |
| `news` | Done | `NewsArticle`, `NewsBatch` |
| `filings` | Done (2A) | `SecFiling`, `SecFilingsBatch` |
| `financials` / others | Done (2C.2) | Enriched `FinancialMetrics` (= `FundamentalsSnapshot`); series + statement summaries |
| `fundamentals_minimum` | Done | Editable min field paths for soften Yahoo-fatal (2C.3 gate) |
| `watchlist` | Done | Membership + ticker summaries for dashboard |
| `portfolio` | Done (v2) | `PortfolioRiskSnapshot` + `PairCorrelation` |
| `brief` | Done (Slice 1) | `DailyBrief` / `BriefTicker` / `BriefBullet` |
| `financials.history_closes` | Done | Yahoo daily closes on source-cache payload (Risk + Brief) |

---

## Memory

| Module | Status |
|--------|--------|
| All | Todo (deferred past thin Phase 2) |

---

## Suggested next milestones

1. Dogfood Brief Slice 1 (Assignment timing ≤30m) + founder miss log
2. Phase 3 evidence deepen in detail panel (claim↔evidence; design 8A)
3. Phase0 server single-flight if concurrent refresh still burns cost

---

## Changelog

| Date | Change |
|------|--------|
| 2026-08-03 | Flexible ticker intake: extract/dedupe, `/api/watchlist/intake`, CSV/paste/speech/OCR UI |
| 2026-08-03 | Daily Decision Brief Slice 1: generator, API, BriefPage, yahoo_history, history_closes on Yahoo metrics |
| 2026-07-31 | Correlation slice (Risk v2): `PairCorrelation`, Yahoo `history_closes` Pearson pairs, RiskPage table |
| 2026-07-30 | Portfolio Risk v1: schemas, `GET /api/risk`, `RiskPage` + `PrimaryNav` |
| 2026-07-25 | Watchlist dashboard v1: FastAPI + Svelte 5 UI over Phase0Result |
| 2026-07-25 | Alpha Vantage fill-gaps: OVERVIEW → forward/market fields; optional key; soft-fail |
| 2026-07-25 | Phase 2C.3 done: `sec_xbrl`, `merge_fundamentals`, soften Yahoo-fatal |
| 2026-07-25 | Lock 2C.3 min fundamentals field set + unit tests (`fundamentals_minimum`) |
| 2026-07-25 | Docs aligned: PRD/TODOS/architecture reflect 2C.1–2C.2 shipped; 2C.3 next |
| 2026-07-25 | Phase0Result.fundamentals + root agent full-JSON presentation for debugging |
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
