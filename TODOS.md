# TODOS

Deferred work from CEO plan review (2026-07-21) and eng/office-hours design (2026-07-25). Phase 1–2B shipped. Phase 2C complete. Watchlist dashboard v1 **shipped**. Watchlist design polish **shipped** (2026-07-28). Portfolio Risk v1 (Held concentration) **shipped** (2026-07-30). Correlation slice (Risk v2) **shipped** (2026-07-31). **Daily Decision Brief** designed APPROVED (2026-07-31) — Slice 1 queued next. Then Phase 3 evidence deepen, or Phase0 server single-flight if cost bites — see [docs/architecture.md](docs/architecture.md).

**Design:** [DESIGN.md](DESIGN.md) · living UX plan [docs/design-plan.md](docs/design-plan.md) (`/plan-design-review` 2026-07-28). Brief design: `~/.gstack/projects/schohan-foliotracker/shailenderchohan-main-design-20260731-024904.md`.

**Phase 2 lock (2026-07-24):** Thin Phase 2 = **SEC specialist → scoring service**. Portfolio and cache/memory deferred.

**Thin Phase 2 complete** = 2A + 2B (**both done 2026-07-24**).

**Phase 2C lock (2026-07-25):** Provider port + per-source cache; Yahoo enrich day-1; SEC XBRL; Alpha Vantage fill-gaps. No Kafka.

## Next milestones (queued)

### Daily Decision Brief — Slice 1 (2026-07-31)

**What:** Portfolio-scoped daily triage for Held ∪ Watched: material-event bullets with optional source URLs + metrics strip; thin Brief page in nav; Generate today (cache-first); miss log; persist last 14 Briefs.

**Why:** Founder dogfood ritual is ~4h/day of Yahoo + broker tabs across ~40 names; target ≤30 minutes while keeping a full-time job. Win by ruthless omission + ranking, not more news. Cite-first on the existing evidence spine.

**Defaults (tunable after dogfood):** rolling 24h window; gate = \|daily return\| ≥ 5% OR material event; rank `max(move_score, event_severity)`; cap 15 tickers / 5 bullets; keyword categories first; **bullets = evidence titles (no LLM in Slice 1)**.

**Eng locks (`/plan-eng-review` 2026-07-31):**
- Sync `POST` Generate + ~60s wall budget → `generation_status` complete/stale/partial (no Celery)
- Shared `yahoo_history` helper (extract from Risk); blocking daily-% spike; news/SEC-only gate fallback
- Data plane: source caches + `evidence_from_*` (not `run_phase0_research`); Phase0 cache optional for metrics strip
- `brief_classify` module + tests; `brief_store` (ring 14 + miss log JSONL); bounded thread pool (4–8)
- Slice 1 PR **must** update `docs/architecture.md` + `docs/implementation-status.md`
- Tests: complete pytest for classify/history/gate/rank/store/API; Risk correlation regression mandatory; E2E optional

**Blocking pre-work:** Confirm daily % via shared history helper from Yahoo `history_closes`; smoke-test cold-cache ~40-ticker Generate vs rate limits. If no daily %, ship news/SEC-only gate.

**Out of Slice 1 build:** dissemination (email, messaging, audio, MCP — **recorded** in PRD only); social (Reddit/X); full earnings-call digests; scheduled generation; Brief history browse UI; LLM bullet phrasing (see Slice 1b).

**Invariant:** Social signals (when added later) render in a separate section and **must not** feed scorecard, risk, or Brief ranking.

**Effort:** M  
**Priority:** P1  
**Depends on:** Watchlist Held/Watched (done); 2C news/cache (done); daily-% spike  
**Design:** office-hours APPROVED 2026-07-31 (Approach B)

### Daily Decision Brief — Slice 1b — LLM phrasing (default off)

**What:** Optional LLM bullet phrasing behind settings flag (default **off**); fail-closed discard if uncited; unit tests.

**Why:** PRD allowed optional LLM; Slice 1 correctly ships headline bullets to protect sync budget and sole-LLM=thesis invariant.

**Context:** Reuse thesis-style citation checks; do not enable by default until Generate budget is proven in dogfood. Start at `brief_service` + settings.

**Effort:** M  
**Priority:** P2  
**Depends on:** Brief Slice 1 shipped + Assignment timing OK

### Daily Decision Brief — Slice 2 (after Assignment)

**What:** Polish, scheduled generation, Brief history browse.

**Why:** Only after timed Assignment comparison supports ≤30m bar.

**Effort:** M  
**Priority:** P2  
**Depends on:** Brief Slice 1 dogfood + Assignment validation

### Brief — Phase-next (recorded)

**What:** Social display-only section; earnings-call summary bullets; dissemination adapters (messaging, audio soundbite, MCP, email) over the same `DailyBrief` object.

**Why:** Completeness of the product vision; do not build until website Brief is trusted.

**Effort:** L  
**Priority:** P3  
**Depends on:** Brief Slice 1 trusted in dogfood

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
