# TODOS

Deferred work from CEO plan review (2026-07-21) and eng/office-hours design (2026-07-25). Phase 1–2B shipped. Phase 2C complete. Watchlist dashboard v1 **shipped**. Watchlist design polish **shipped** (2026-07-28). Portfolio Risk v1 (Held concentration) **shipped** (2026-07-30). Correlation slice (Risk v2) **shipped** (2026-07-31). **Daily Decision Brief Slice 1 shipped** (2026-08-03). **Brief triage dashboard (Impact Score, High/Medium/Quiet, filters, history, drawer, heat map, insight modes) shipped** (2026-08-04). **Flexible ticker intake shipped** (2026-08-03). **Watchlist bulk ops shipped** (2026-08-03). **Portfolio Intelligence vision adopted — docs locked** (2026-08-05). **Thesis T1 shipped** (2026-08-07). **Thesis T2 shipped** (2026-08-07). Next: Thesis T3 (Thesis Monitoring), orthogonal collections (1A), Brief dogfood with `BRIEF_INSIGHT_MODE=llm` in staging, Phase 3 evidence deepen, or Phase0 server single-flight if cost bites — see [docs/architecture.md](docs/architecture.md).

**Portfolio Intelligence (2026-08-05):** Umbrella vision in [docs/PRD.md](docs/PRD.md) §1: six engines; shipped Brief = Engine 1 surface (**preserved unchanged**); new Thesis landing page hosts Engines 2–6. Directive guidance only from the AI Portfolio Advisor. Thesis slices T1–T5 + Brief E1 below.

**Design:** [DESIGN.md](DESIGN.md) · living UX plan [docs/design-plan.md](docs/design-plan.md) (`/plan-design-review` 2026-07-28). Brief design: `~/.gstack/projects/schohan-foliotracker/shailenderchohan-main-design-20260731-024904.md`.

**Phase 2 lock (2026-07-24):** Thin Phase 2 = **SEC specialist → scoring service**. Portfolio and cache/memory deferred.

**Thin Phase 2 complete** = 2A + 2B (**both done 2026-07-24**).

**Phase 2C lock (2026-07-25):** Provider port + per-source cache; Yahoo enrich day-1; SEC XBRL; Alpha Vantage fill-gaps. No Kafka.

## Next milestones (queued)

### Thesis T3 — Thesis Monitoring

**What:** Per-ticker thesis snapshot ring store (like `brief_store`). Quarterly change assessment → closed verdict set `No change | Strengthened | Slightly weaker | Broken` with cited evidence. `thesis/ThesisTimeline` UI. LLM narrative behind `THESIS_INSIGHT_MODE=deterministic|canned|llm`, fail-closed like `brief_insight`.

**Why:** Engine 5 (PRD §5.4.4): monitor thesis, not price — the core long-term-investor value.

**Effort:** M  
**Priority:** P2  
**Depends on:** T1; existing `InvestmentThesis` from Phase 0 seeds the original thesis

### Thesis T4 — AI Portfolio Advisor + AI Research button

**What:** Advisor insight per holding: reasoning lines + directive conclusion (buy more / hold / trim / research further / wait) + confidence, per PRD §5.4.5 reference example. `POST /api/thesis/explain` research button with canned framework questions (PRD §5.4.10), patterned on `POST /api/brief/explain`. Provider label always visible; fail-closed.

**Why:** Engine 6 — the only surface allowed directive phrasing (PRD principle 7).

**Effort:** M  
**Priority:** P2  
**Depends on:** T1–T3 signals (frameworks, valuations, thesis verdicts)

### Thesis T5 — Investment OS Score + Portfolio dashboard

**What:** Deterministic composite from the locked weight table (PRD §5.4.11: Business Quality 20 / Financial Strength 15 / Valuation 20 / Balance Sheet 15 / Earnings Quality 10 / Capital Allocation 10 / Framework Consensus 5 / Thesis Stability 5). Portfolio health rollup counts (PRD §5.4.8) on the Thesis page.

**Effort:** M  
**Priority:** P3  
**Depends on:** T1–T3 (consensus + stability inputs)

### Brief E1 — event enrichment + morning counts (additive)

**What:** **Additive optional** `BriefBullet` fields: impact, confidence, affected frameworks, thesis impact. Morning count strip (thesis changed / valuation improved / MoS increased / balance sheet weakened / risk increased / opportunity score, PRD §5.4.9).

**Why:** Engine 1 extension of the shipped Brief. Backwards-compatible by contract: optional fields only; Brief behavior unchanged until this ships; **no shipped Brief acceptance criteria change**. Existing Brief milestones (insight-mode dogfood, Slice 2 polish, E2E smoke, near-miss log) stay queued unchanged.

**Effort:** S–M  
**Priority:** P3  
**Depends on:** Thesis T3 (verdict + valuation-delta signals)

### Thesis — Phase-next frameworks (recorded)

**What:** Remaining framework modules after Graham + Financial Strength: Peter Lynch, Greenblatt Magic Formula, Quality Investing, GARP, Dividend, Momentum. Then future modules: Howard Marks (cycle/risk asymmetry), Munger (qualitative quality), Mauboussin (expectations investing), Fama-French (factor exposures), Behavioral Finance (bias alerts), Macro Overlay (rate/recession/inflation/geopolitical).

**Why:** Investment Intelligence Platform trajectory (PRD §5.4.13); recorded, not sequenced.

**Effort:** L (per module S–M)  
**Priority:** P3  
**Depends on:** T1 framework engine pattern proven

### Watchlist collections (orthogonal overlays — 1A)

**What:** User-defined named collections (Yahoo-style groups) as overlays on Held/Watched membership. Create/rename/delete; add/remove selected tickers; filter watchlist by collection. Risk/Brief stay Held∪Watched (unchanged).

**Why:** Bulk membership ops shipped; organize ~40 names without replacing capital-vs-curiosity lists.

**Effort:** M  
**Priority:** P2  
**Depends on:** Bulk ops shipped (2026-08-03)

### Daily Decision Brief — insight mode dogfood (LLM staging)

**What:** Keep production on `BRIEF_INSIGHT_MODE=deterministic`. Staging: exercise `canned`, then `llm` (Gemini structured insight; fail-closed to deterministic). Confirm Generate budget + honesty of provider label.

**Why:** Triage UI + contract shipped; LLM path exists behind flag but must not be default until dogfood proves cost/latency.

**Context:** `app/services/brief_insight.py`; `POST /api/brief/explain`. Never invent source URLs; reject buy/sell phrasing.

**Effort:** S–M  
**Priority:** P2  
**Depends on:** Brief triage dashboard shipped (2026-08-04)

### Daily Decision Brief — Slice 2 polish (after Assignment)

**What:** Scheduled generation; virtualized lists at 100+ holdings; real position weights when available.

**Why:** History browse + drawer already shipped with triage dashboard; schedule still waits on Assignment timing bar.

**Effort:** M  
**Priority:** P2  
**Depends on:** Brief dogfood + Assignment validation

### Brief — Phase-next (recorded)

**What:** Social display-only section; earnings-call summary bullets; dissemination adapters (messaging, audio soundbite, MCP, email) over the same `DailyBrief` object.

**Why:** Completeness of the product vision; do not build until website Brief is trusted.

**Effort:** L  
**Priority:** P3  
**Depends on:** Brief triage trusted in dogfood

### Brief — E2E Generate smoke

**What:** One browser/E2E smoke: Brief nav → Generate → empty-or-rows; assert Generate disables while in flight (double-submit).

**Why:** Thin `BriefPage` wiring bugs slip past API unit tests.

**Context:** Units+API are the Slice 1 bar; add E2E after harness is reliable (Playwright/browse). Prior learning: watchlist Refresh-all must set per-ticker refreshing — same class of bug for Generate.

**Effort:** S  
**Priority:** P3  
**Depends on:** Brief Slice 1 API + page; working browser test harness

### Brief — near-miss log for keyword tuning

**What:** Append-only near-miss log (e.g. news present + 3–5% move, or unclassified headlines on movers) for keyword tuning — **not** shown in Brief UI v1.

**Why:** Known Slice 1 recall limit when keywords miss flat-price material events; founder miss log alone is sparse.

**Context:** Design residual-risk note; keep out of scores/ranking. Store beside `brief_store` miss log.

**Effort:** S  
**Priority:** P3  
**Depends on:** Brief Slice 1 generator + `brief_store`

### Phase 3 — deepen evidence browser (detail panel)

**What:** Claim↔evidence links and richer evidence browser in `TickerDetailPanel`; optional full-page ticker mode later.

**Why:** Detail panel *is* the Phase 3 research surface (design **8A**); ADK chat stays optional for engineers.

**Context:** Keep `Phase0Result` as the contract. Nav shell now shared with Risk — deepen without inventing a second UI language.

**Effort:** L  
**Priority:** P2  
**Depends on:** Phase 0 product-complete; ideally 2C (done); Risk nav shell (done)

### Phase0 in-flight single-flight (dedupe)

**What:** Server-side single-flight / in-flight dedupe so concurrent `run_phase0_research` calls for the same ticker share one run and one result.

**Why:** UI polish guards the common double-fetch; ADK chat, refresh-all races, or two tabs can still burn duplicate LLM/API cost.

**Pros:** Correct under concurrency; saves money as dogfood grows.

**Cons:** Cancel/timeout semantics need care.

**Context:** Deferred from `/plan-eng-review` performance 4B (2026-07-28). UI single-flight (4A) **shipped** in watchlist polish. Start at `phase0_pipeline` / `watchlist_service`. Opportunistic if dogfood still double-fires.

**Effort:** M  
**Priority:** P3  
**Depends on / blocked by:** None

## Open product decisions (from PRD — not yet sequenced)

### Brief — multi-account tags

**What:** Optional multi-account tags on Brief rows (e.g. taxable vs IRA).

**Why:** PRD open Q; default today is a single Held/Watched book.

**Effort:** S–M  
**Priority:** P3 (decide before Brief Slice 2 if dogfood needs it)  
**Depends on:** Brief Slice 1 dogfood signal  
**Default if undecided:** single book, no tags

### Brief / watchlist — category labels

**What:** Optional category labels (Biotech/AI/…) on watchlist and/or Brief rows.

**Why:** PRD open Q; default for Brief v1 is **no** category labels.

**Effort:** M  
**Priority:** P3  
**Depends on:** Product call after Brief Slice 1  
**Default if undecided:** no categories in v1

## Deferred beyond Risk v2

### Cache / memory beyond Phase 0 TTL files

**What:** Richer ticker/company/session memory; optional shared cache.

**Why:** Cost control and continuity across research sessions.

**Context:** Phase 0 has local file TTL cache; 2C adds per-source files. Memory stubs under `app/memory/` stay untouched until needed.

**Effort:** M  
**Priority:** P3  
**Depends on:** Phase 0 cache proven; 2C per-source cache landed

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

### Position weights / shares (portfolio)

**What:** User-entered shares or % weights instead of equal-weight assumption.

**Why:** Real concentration needs size; v1 deliberately equal-weight.

**Effort:** L  
**Priority:** P3  
**Depends on:** Risk v2 dogfood; product call on local store shape

## Completed

### Thesis T2 — Valuation Engine + Net Asset Intelligence + Margin of Safety (2026-08-07)

- Valuation / MoS / net-asset formula specs **locked** in architecture.md (Graham / Buffett / Modern + ladder + asset verdict bands)
- Schemas: `ValuationMethod` / `ValuationLadder` / `ValuationSet` / `MarginOfSafetyView` / `AssetBreakdown` on `ThesisTicker`
- `thesis_valuations`: deterministic Graham (NCAV cash-proxy, net-net, intrinsic, liquidation, adjusted book, MoS), Buffett (FCF owner-earnings proxy, FCF yield, capital efficiency, margin pass-through; ROIC always null), Modern (Gordon DCF r=10%/g≤4%, reverse DCF, EV multiples, PEG; historical bands + sector relative always null); six-value ladder (Replacement null); Expected Fair = median of Intrinsic/DCF/Adjusted book
- `thesis_net_assets`: honest line gaps; adjusted = assets − liabilities; difference % + undervaluation/fair/overvaluation verdict
- Same Generate path — no new API routes; `build_thesis_ticker` attaches valuation / MoS / assets
- UI: `ValuationLadder`, `MarginOfSafety`, `AssetBreakdown` + method school tables on ticker drill-down; format helpers + Vitest
- Tests: valuation + net-asset units green; framework/API regression green; Brief untouched

### Thesis T1 — landing page shell + Framework Engine v1 (2026-08-07)

- Pre-T1 gate cleared: Graham + Financial Strength formulas/thresholds **locked** in architecture.md "Framework formula specs" (weights, bands, coverage rule) with unit tests before anything consumes scores
- Schemas: `FrameworkCheck` / `FrameworkScorecard` / `ThesisTicker` / `ThesisDashboard` (`app/schemas/thesis.py`)
- `thesis_frameworks`: deterministic Graham Deep Value + Financial Strength; honest `null` checks (Dividend History has no source; Altman Z / Piotroski F excluded — inputs unavailable); score `null` below 50 weight coverage
- `thesis_service.generate_thesis_dashboard`: cache-first Yahoo + SEC XBRL (+ AV when keyed) → `merge_fundamentals` → scorecards; wall budget + bounded pool; no `run_phase0_research`
- `thesis_store`: dashboard ring (`THESIS_STORE_PATH`, ring 14); `THESIS_GENERATE_BUDGET_SECONDS` / `THESIS_MAX_WORKERS`
- API: `GET /api/thesis`, `POST /api/thesis/generate`
- UI: `ThesisPage` + `thesis/FrameworkScoreTable` + `thesis/FrameworkScorecard`; `PrimaryNav` → `Watchlist | Risk | Brief | Thesis`; `thesisFormat` helpers
- Tests: 34 backend (formulas/store/service/API) + 12 Vitest format; full suites green; Brief untouched

### Watchlist bulk ops (2026-08-03)

- Multi-select checkboxes + per-section select-all on Held/Watched tables
- Bulk bar: Move to Held / Move to Watched / Remove / Clear (membership-only; no research; no confirm)
- API: `POST /api/watchlist/bulk` (`remove` | `move_to_held` | `move_to_watched`)
- Store: `bulk_remove` / `bulk_move` with `affected` / `skipped_not_found` / `skipped_noop`
- Collections (1A overlays) deferred — see queued milestone above

### Flexible ticker intake (2026-08-03)

- `ticker_intake`: shared extract for CSV / paste / OCR text / speech transcript → `normalize_ticker`
- Dedupe: already on Held ∪ Watched skipped (no list move, no research); within-upload collapse
- Counts: `added` / `skipped_duplicate` / `rejected_invalid`; empty extract → 400
- API: `POST /api/watchlist/intake`
- UI: `TickerIntakePanel` — CSV file, paste, Speak (Web Speech API), Screenshot (tesseract.js OCR)
- Optional CSV `list`/`kind` column; else user-selected Held/Watched
- Unit tests: extract, skip-existing, CSV kinds, API

### Daily Decision Brief — Slice 1 (2026-08-03)

- Schemas: `DailyBrief` / `BriefTicker` / `BriefBullet` (`app/schemas/brief.py`)
- `yahoo_history`: shared parse + last-session daily % + `move_score`; Risk refactored to use it
- Yahoo `FinancialMetrics.history_closes` persisted in source cache (excluded from evidence IDs)
- `brief_classify`: keyword + SEC form heuristics; severity table unit-tested
- `brief_service.generate_daily_brief`: cache-first fan-out (not `run_phase0_research`); ~60s wall; pool 4–8; gate/rank/cap 15/5
- `brief_store`: ring-14 + miss-log JSONL
- API: `GET /api/brief`, `POST /api/brief/generate`, `POST /api/brief/miss`
- UI: `BriefPage` + `PrimaryNav` Brief; Generate / force-refresh / ranked rows / miss log
- Docs: architecture + implementation-status updated
- Tests: classify/history/store/service/API + Risk regression green

### Daily Decision Brief — triage dashboard (2026-08-04)

- Schemas: Impact Score, priority, sentiment, `BriefInsight`, `BriefSummary`, `quiet_tickers`, `insight_mode`
- `brief_impact.py` + `brief_insight.py` with `BRIEF_INSIGHT_MODE=deterministic|canned|llm` (llm fail-closed)
- Generator: enrich bullets, quiet list, portfolio summary / morning digest fields
- API: `GET /api/brief/history`, `POST /api/brief/explain`
- UI: PortfolioSummary, FilterBar, EventRow, PrioritySection, HeatMap, TimelineRail, StockDrawer
- Unread via localStorage; keyboard j/k + Enter
- Tests: impact, insight modes, service quiet/summary, history + explain API

### Correlation slice — portfolio Risk v2 (2026-07-31)

- Schemas: `PairCorrelation` on `PortfolioRiskSnapshot` (`top_correlations`, `correlation_pairs_known`)
- Service: Pearson pairwise daily returns from Yahoo source-cache `history_closes` (stale OK; no live refetch)
- Top N by |correlation|; skip pairs with &lt; 60 overlapping return days; window `~1y daily returns`
- UI: `RiskPage` **Top correlations** table; `formatCorrelation` helper
- Gaps/`partial` when Held ≥ 2 and history/overlap missing
- Unit tests: empty / one / high corr / missing history / insufficient overlap / sort by abs

### Portfolio Risk v1 — Held concentration (2026-07-30)

- Schemas: `PortfolioRiskSnapshot`, `HeldPositionRisk`, `SectorBucket` (`app/schemas/portfolio.py`)
- Service: equal-weight concentration from Held + Phase0 cache / summaries (`portfolio_risk_service`)
- FastAPI `GET /api/risk`; no research re-run
- UI: text nav `Watchlist | Risk` (design 7A); `RiskPage` sector + names tables; empty Held warm CTA
- Status `partial` when sector/risk gaps; disclaimer always present
- Unit tests: empty / one / multi-sector / missing sector / cache miss; Vitest format helpers

### Watchlist design polish (2026-07-28)

- First-run collapsed IA (1A): brand + warm tagline + add form; hide empty Held/Watched shells
- Warm one-sided sibling empties + prefill list kind cue
- Static research wait line + `aria-live="polite"`; UI single-flight (no `fetchResearch` while refreshing; refresh-all flags all tickers)
- Membership-first Add (form unlocks after POST); “Adding…” / “Refreshing…” busy labels
- Error banner Retry; warm detail gap copy; conflict-empty calm success
- ConflictsList: no left border; topic / severity meta / soft summary (4A)
- Mobile &lt;640px block rows + full-viewport detail sheet; Escape + focus return; focus trap; 44px targets; `main` landmark
- Vitest helpers: `listVisibility`, `researchWaitCopy`, Escape/`rowFocusId`

### Watchlist dashboard v1 (2026-07-25)

- FastAPI (`app/api`) over `run_phase0_research`; local JSON membership (held/watched)
- Svelte 5 + Vite UI (`web/`): rows, refresh, detail panel, disclaimer
- Summaries derived from `Phase0Result` only — no auto buy/trim signals
- Design lock: navy/paper/copper accent, Fraunces + IBM Plex Sans

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
