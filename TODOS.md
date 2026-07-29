# TODOS

Deferred work from CEO plan review (2026-07-21) and eng/office-hours design (2026-07-25). Phase 1–2B shipped. Phase 2C complete. Watchlist dashboard v1 **shipped** (FastAPI + Svelte 5). Next: portfolio/correlation layer or Phase 3 polish — see [docs/architecture.md](docs/architecture.md).

**Design:** [DESIGN.md](DESIGN.md) · living UX plan [docs/design-plan.md](docs/design-plan.md) (`/plan-design-review` 2026-07-28).

**Phase 2 lock (2026-07-24):** Thin Phase 2 = **SEC specialist → scoring service**. Portfolio and cache/memory deferred.

**Thin Phase 2 complete** = 2A + 2B (**both done 2026-07-24**).

**Phase 2C lock (2026-07-25):** Provider port + per-source cache; Yahoo enrich day-1; SEC XBRL; Alpha Vantage fill-gaps. No Kafka.

## Watchlist design polish (from `/plan-design-review` 2026-07-28)

### First-run + warm empty lists

**What:** Collapsed first-run when zero tickers (brand + tagline + add form only; hide Held/Watched shells). When only one list has rows, show the empty sibling with warm copy that points at Add (and list kind).

**Why:** Empty spreadsheet chrome kills the first five seconds; first visit should invite the primary action.

**Pros:** Highest-impact dogfood UX; small surface; locks decision 1A.

**Cons:** `WatchlistPage` empty/one-sided/populated matrix needs care.

**Context:** [docs/design-plan.md](docs/design-plan.md) IA + interaction states; [DESIGN.md](DESIGN.md).

**Effort:** S  
**Priority:** P1  
**Depends on / blocked by:** None

### Research wait stage line

**What:** While a ticker is researching/refreshing, keep the row visible and show a muted **static** honest line describing the research job (e.g. “Researching — fundamentals, news, filings, thesis…”). Use `aria-live="polite"`. No rotating fake stages. No determinate progress bar. While that ticker is refreshing, detail panel must not call `fetchResearch` (UI single-flight — eng E4/4A).

**Why:** Silent pulse during multi-source fetch feels broken; fake stage rotation would lie about pipeline position.

**Pros:** Locks design 3A + eng E1/1A + E4/4A; small UI change; big trust/cost win.

**Cons:** Copy is approximate about *what* the system does, not *where* it is.

**Context:** [docs/design-plan.md](docs/design-plan.md) journey + eng decisions; decision 3A / E1 / E4.

**Effort:** S  
**Priority:** P1  
**Depends on / blocked by:** None for client-only copy; streaming API explicitly out of polish scope

### Conflicts list chrome (no left border)

**What:** Restyle `ConflictsList` — remove copper left border; topic strong type, severity small uppercase meta, summary soft ink.

**Why:** Colored left-border cards read as generic SaaS; conflicts should feel like structured disagreement.

**Pros:** Tiny change; removes the hard AI-slop hit; locks decision 4A.

**Cons:** Negligible.

**Context:** `web/src/lib/components/ConflictsList.svelte`; [DESIGN.md](DESIGN.md); decision 4A.

**Effort:** XS  
**Priority:** P2  
**Depends on / blocked by:** None

### Mobile layout + keyboard/a11y

**What:** Below 640px use block list rows (not a card mosaic) and a full-viewport detail sheet. Escape closes detail and returns focus to the opening row; focus trap on the mobile sheet; 44×44px minimum tap targets; wrap page in `main` landmark.

**Why:** Horizontal-scroll tables are hostile one-handed; keyboard users can tab into the list behind an open panel.

**Pros:** Locks decision 6A + focus rules; real phone dogfood.

**Cons:** Largest polish item; careful CSS for table↔block switch.

**Context:** [docs/design-plan.md](docs/design-plan.md) Pass 6; [DESIGN.md](DESIGN.md).

**Effort:** M  
**Priority:** P1  
**Depends on / blocked by:** None (fine after first-run polish)

### Interaction-state copy pass

**What:** Replace bare empties (“No thesis.”, “No scorecard.”) with warm gap copy from the design-plan states table; conflict-empty as calm success; page error banner with Retry; “Adding…” / “Refreshing…” labels on busy controls.

**Why:** Sparse failure copy makes partial/error runs feel broken instead of honest.

**Pros:** Cheap; finishes Pass 2 in the product; pairs with first-run TODO.

**Cons:** Easy to overwrite — stay utility tone per DESIGN.md.

**Context:** [docs/design-plan.md](docs/design-plan.md) interaction states; [DESIGN.md](DESIGN.md).

**Effort:** S  
**Priority:** P2  
**Depends on / blocked by:** None

## Deferred beyond Phase 2C

### Portfolio / correlation layer

**What:** Multi-ticker orchestration, concentration, and correlation-aware risk.

**Why:** Product is FolioTracker; Phase 0 is single-ticker only.

**Context:** `portfolio_agent` stub exists. Needs portfolio schemas, batch evidence, and risk services. Do not start until single-ticker spine + scoring + 2C fundamentals are trusted.

**Design lock (2026-07-28):** Same app shell as watchlist; simple text nav `Watchlist | Risk`; shared [DESIGN.md](DESIGN.md) tokens — not a second visual language ([docs/design-plan.md](docs/design-plan.md) decision 7A).

**Effort:** XL  
**Priority:** P2  
**Depends on:** Thin Phase 2 (done); preferably 2C richer fundamentals

### Cache / memory beyond Phase 0 TTL files

**What:** Richer ticker/company/session memory; optional shared cache.

**Why:** Cost control and continuity across research sessions.

**Context:** Phase 0 has local file TTL cache; 2C adds per-source files. Memory stubs under `app/memory/` stay untouched until needed.

**Effort:** M  
**Priority:** P3  
**Depends on:** Phase 0 cache proven; 2C per-source cache landed

### Phase0 in-flight single-flight (dedupe)

**What:** Server-side single-flight / in-flight dedupe so concurrent `run_phase0_research` calls for the same ticker share one run and one result.

**Why:** UI polish guards the common double-fetch; ADK chat, refresh-all races, or two tabs can still burn duplicate LLM/API cost.

**Pros:** Correct under concurrency; saves money as dogfood grows.

**Cons:** Cancel/timeout semantics need care; not needed for the polish PR.

**Context:** Deferred from `/plan-eng-review` performance 4B (2026-07-28). UI single-flight (4A) ships in watchlist polish. Start at `phase0_pipeline` / `watchlist_service`.

**Effort:** M  
**Priority:** P3  
**Depends on / blocked by:** None; fine after watchlist polish lands

## Phase 3 — Platform

### Custom API / UI beyond `adk web`

**What:** First-party HTTP API and/or minimal research UI.

**Why:** Real users won’t live in ADK’s default chat forever.

**Context:** Watchlist API/UI shipped. Design review done 2026-07-28. Keep Phase0Result as the contract.

**Design lock (2026-07-28):** Detail panel *is* the Phase 3 research surface — deepen evidence browser + claim↔evidence links; optional full-page ticker mode; ADK chat remains optional for engineers ([docs/design-plan.md](docs/design-plan.md) decision 8A; [DESIGN.md](DESIGN.md)).

**Effort:** L  
**Priority:** P3  
**Depends on:** Phase 0 product-complete; ideally 2C

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

## Completed

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
