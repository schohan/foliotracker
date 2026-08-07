# Implementation Status

Tracks what exists vs. what is still scaffold-only, relative to [architecture.md](architecture.md).

**Active scope:** Thin Phase 2 + **2C done**. Watchlist + Risk v2 **shipped**. **Daily Decision Brief Slice 1 + triage dashboard shipped** (Engine 1 surface). **Brief E1 shipped (2026-08-07)** — morning counts + bullet thesis linkage. **Flexible ticker intake shipped**. **Thesis T1–T5 shipped (2026-08-07)**. **Next:** Brief dogfood Assignment or watchlist collections (1A). See [TODOS.md](../TODOS.md).

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
| Watchlist HTTP API (`app/api`) | Done | FastAPI: membership, intake, refresh, research GET, risk, brief (get/history/generate/miss/explain), thesis (get/generate) |
| Watchlist store / service | Done | Local JSON + `Phase0Result` → summary |
| Watchlist UI (`web/`) | Done | Svelte 5 dashboard (held/watched, detail panel, flexible intake) |
| Ticker intake service / API / UI | Done | `ticker_intake` + `POST /api/watchlist/intake` + `TickerIntakePanel` |
| Portfolio risk service | Done (v2) | Held equal-weight concentration + pairwise corr from Yahoo source-cache history |
| Risk UI (`RiskPage` + `PrimaryNav`) | Done (v2) | `Watchlist \| Risk \| Brief \| Thesis`; sector + names + top correlations tables |
| Brief service / store / classify / insight | Done | Gate/rank Generate; Impact Score + priority; insight provider (`BRIEF_INSIGHT_MODE` deterministic/canned/llm, fail-closed); ring-14 + history browse + miss log; E1 morning counts + thesis bullet linkage; no Phase0 research |
| Brief UI (`BriefPage` triage dashboard) | Done | High/Medium/Quiet sections, filters, morning digest strip, E1 Today's Portfolio counts, history timeline, heat map, stock drawer, miss log (`brief/*` components) |

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
| `brief_classify` / `brief_store` / `brief_service` / `brief_insight` / `brief_e1` | Done — insight provider fail-closed; E1 morning counts + thesis bullet linkage |
| `thesis_frameworks` / `thesis_valuations` / `thesis_net_assets` / `thesis_monitor` / `thesis_insight` / `thesis_advisor` / `thesis_os_score` / `thesis_service` / `thesis_store` | Done (T1–T5) — full Thesis page engines; cache-first fan-out; dashboard + per-ticker snapshot rings |
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
| `brief` | Done | `DailyBrief` / `BriefTicker` / `BriefBullet` / `BriefInsight` / `BriefMorningCounts`; triage + E1 fields |
| `thesis` | Done (T1–T3) | Framework + valuation + `ThesisMonitoring` / snapshots; T4+ contracts pending |
| `financials.history_closes` | Done | Yahoo daily closes on source-cache payload (Risk + Brief) |

---

## Memory

| Module | Status |
|--------|--------|
| All | Todo (deferred past thin Phase 2) |

---

## Portfolio Intelligence — Thesis page (planned 2026-08-05)

Contracts and slices: [architecture.md](architecture.md) "Portfolio Intelligence — Thesis page" + [PRD](PRD.md) §5.4. Shipped Brief rows above are unaffected (Engine 1 surface, preserved).

| Item | Status | Notes |
|------|--------|-------|
| Framework formula spec tables (architecture.md) | Done (T1) | Graham + Financial Strength formulas/thresholds **locked 2026-08-07** in architecture.md "Framework formula specs" |
| Valuation / net-asset formula spec tables (architecture.md) | Done (T2) | Graham / Buffett / Modern + ladder + MoS stars + asset verdicts **locked 2026-08-07** |
| Thesis monitoring verdict specs (architecture.md) | Done (T3) | Signal vector + Broken/weaker/strengthened/no-change + quarter gate **locked 2026-08-07** |
| Advisor conclusion specs (architecture.md) | Done (T4) | Priority table + confidence + research question ids **locked 2026-08-07** |
| Investment OS Score specs (architecture.md) | Done (T5) | Dimension weights/formulas + portfolio rollup counts **locked 2026-08-07** |
| `app/schemas/thesis.py` | Done (T1–T5) | Frameworks + valuation + monitoring + advisor + `InvestmentOSScore` / `PortfolioHealthRollup` |
| Framework engine service (Graham + Financial Strength first) | Done (T1) | `thesis_frameworks` — deterministic; unit tests with the spec lock |
| Valuation service (Graham / Buffett / Modern sets, six-value ladder) | Done (T2) | `thesis_valuations`; Replacement / ROIC / historical bands / sector relative stay `null` |
| Net asset service (Adjusted Net Assets vs market cap) | Done (T2) | `thesis_net_assets` |
| Thesis snapshot store + change verdicts | Done (T3) | Per-ticker ring in `thesis_store`; `thesis_monitor` + `thesis_insight` (`THESIS_INSIGHT_MODE`) |
| Advisor + explain service (`THESIS_INSIGHT_MODE`, fail-closed) | Done (T4) | `thesis_advisor`; only surface allowed directive phrasing; `POST /api/thesis/explain` |
| Investment OS Score composite | Done (T5) | `thesis_os_score`; portfolio health rollup on dashboard |
| Thesis HTTP API (`GET /api/thesis`, `POST /api/thesis/generate`, `POST /api/thesis/explain`) | Done (T1+T4) | Generate carries T2–T5 fields; explain uses latest dashboard row |
| `ThesisPage` + `thesis/*` UI; `PrimaryNav` adds Thesis | Done (T1–T5) | Score table + OS + PortfolioHealth + valuation + timeline + advisor |
| Brief E1 enrichment (optional `BriefBullet` fields + morning counts) | Done (E1) | Specs locked; `brief_e1`; MorningCounts UI; after T3 |

---

## Suggested next milestones

1. Dogfood Brief Slice 1 (Assignment timing ≤30m) + founder miss log
2. Watchlist collections (1A overlays)
3. Phase 3 evidence deepen in detail panel (claim↔evidence; design 8A)
4. Phase0 server single-flight if concurrent refresh still burns cost

---

## Changelog

| Date | Change |
|------|--------|
| 2026-08-07 | Brief E1 shipped: enrichment specs locked, `BriefMorningCounts`, `brief_e1`, MorningCounts UI + bullet thesis linkage |
| 2026-08-07 | Thesis T5 shipped: OS Score specs locked, `thesis_os_score`, PortfolioHealth + OSScorecard UI; Thesis T1–T5 complete |
| 2026-08-07 | Thesis T4 shipped: advisor conclusion specs locked, `thesis_advisor`, `AdvisorInsight`, `POST /api/thesis/explain`, AdvisorInsight + ResearchButton UI |
| 2026-08-07 | Thesis T3 shipped: monitoring verdict specs locked, per-ticker snapshots, `thesis_monitor`/`thesis_insight`, `ThesisTimeline` UI |
| 2026-08-07 | Thesis T2 shipped: valuation/MoS/net-asset formula specs locked, `thesis_valuations` + `thesis_net_assets`, schemas on `ThesisTicker`, UI ladder + MoS + asset breakdown |
| 2026-08-07 | Thesis T1 shipped: locked formula specs, `thesis` schemas, `thesis_frameworks` engine, `thesis_service` + `thesis_store`, `GET/POST /api/thesis*`, `ThesisPage` + `thesis/*` UI, nav adds Thesis |
| 2026-08-06 | Align to Portfolio Intelligence docs: Brief rows updated to shipped triage dashboard (2026-08-04 — `brief_insight`, `BriefInsight`, history/explain API, `brief/*` UI components); pre-T1 framework formula-lock gate row added; scope line reflects Brief dogfood → Thesis T1 sequence |
| 2026-08-05 | Portfolio Intelligence (Thesis page) planned rows added: schemas, framework/valuation/net-asset services, snapshot store, advisor, API, UI, Brief E1 |
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
