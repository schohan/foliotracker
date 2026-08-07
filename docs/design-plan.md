# FolioTracker Design Plan

**Status:** Living plan from `/plan-design-review` (2026-07-28); updated 2026-08-06 for the **Portfolio Intelligence** platform framing ([PRD §1](PRD.md))  
**Surfaces:** Shipped — Watchlist (incl. flexible intake), Risk, **Brief triage dashboard (Engine 1 — preserved unchanged)**. Planned — **Thesis landing page (Engines 2–6)**, sequenced in [TODOS.md](../TODOS.md)  
**Classifier:** App UI (workspace-driven, data-dense, task-focused)  
**Visual lock (shipped):** navy/paper/copper · Fraunces (display) + IBM Plex Sans (body) · CSS vars in `web/src/app.css`  
**Design system:** [DESIGN.md](../DESIGN.md)

Related: [PRD.md](PRD.md) · [architecture.md](architecture.md) · [TODOS.md](../TODOS.md) · [DESIGN.md](../DESIGN.md)

---

## Information architecture

### Primary workspace (Watchlist page)

Constraint worship — if the user can only notice **3 things**, they are:

1. **Brand + job** — “FolioTracker” + one line: held/watched names, evidence/scores/thesis at a glance
2. **Primary action** — Add ticker (held vs watched)
3. **Lists** — Held first, Watched second (owned capital before curiosity)

Secondary context (not in the first three): Refresh all, per-row refresh/remove, disclaimer, detail panel.

**IA score:** 10/10 (decision 1A locked 2026-07-28)

### First-run composition (both lists empty) — **1A locked**

Hide Held/Watched section headers and stub empty copy until at least one ticker exists.

```
┌─────────────────────────────────────────────────────────────┐
│  FolioTracker                                               │
│  Add a ticker to start grounded research.                   │
│  [Add ticker] [Watched ▾] [Add]                             │
│  (no Refresh all until lists exist)                         │
│  Disclaimer                                                 │
└─────────────────────────────────────────────────────────────┘
```

Warmth: supporting line invites the first add. Primary action is the only workspace control. After first successful add, reveal the matching section (Held or Watched) and show Refresh all.

### Populated composition

```
┌─────────────────────────────────────────────────────────────┐
│  FolioTracker                          (display, loudest)   │
│  Held and watched — evidence, scores, thesis at a glance    │
├─────────────────────────────────────────────────────────────┤
│  [Add ticker] [Watched ▾] [Add]          [Refresh all]      │
├─────────────────────────────────────────────────────────────┤
│  HELD                                                           │
│  Ticker │ Status │ G/V/R │ Fwd P/E │ Conflicts │ Thesis │ …   │
│  …rows…                                                         │
├─────────────────────────────────────────────────────────────────┤
│  WATCHED                                                        │
│  …same columns…                                                 │
├─────────────────────────────────────────────────────────────────┤
│  Disclaimer (always visible, non-advice)                        │
└─────────────────────────────────────────────────────────────────┘
         │ select row
         ▼
┌──────────────────────┐
│ Detail panel (right) │  hierarchy below
└──────────────────────┘
```

Show a section only when it has rows **or** when the other section has rows (so a one-sided list still shows the empty sibling with warm empty copy + CTA to add into that list). Exception: true first-run (zero tickers total) uses the collapsed composition above.

### Detail panel hierarchy (when a ticker is selected)

1. **Ticker + status** (identity + honesty label: ok / partial / error)
2. **Scorecard** (glanceable dimensions — why you opened the row)
3. **Thesis** (cited narrative)
4. **Conflicts** (trust: where sources disagree)
5. **Fundamentals** (numbers that ground the thesis)
6. **Raw JSON** (collapsed `<details>` — power-user / debug only)
7. **Meta** — request_id, cache_hit

### Navigation

*(Superseded 2026-08-06 — original v1 was single-page with no global nav.)* Shipped nav is `PrimaryNav`: **Watchlist | Risk | Brief** (text nav, same shell, per 7A). The planned Thesis landing page extends it to **Watchlist | Risk | Brief | Thesis** ([PRD §5.4](PRD.md)). Watchlist stays home default. Close detail returns focus to the list. No marketing shell.

### Deferred IA (TODOS — sketched)

| Surface | Job | First / second / third |
|---------|-----|------------------------|
| Portfolio / correlation | Multi-ticker risk | **7A — shipped (Risk v2):** same shell; text nav; Risk view is primary workspace when selected; watchlist stays home default |
| **Thesis landing page (Engines 2–6)** | Answer the five morning questions per holding through multiple framework lenses | Planned (T1+): nav adds Thesis; page hosts framework score table, valuation ladder, thesis timeline, advisor insight — see [Thesis surface](#thesis-surface-planned--portfolio-intelligence-engines-26) below |
| Phase 3 research UI | Single-ticker deep research without ADK chat | **8A:** detail panel *is* the research UI — deepen evidence/claim links; optional full-page mode; ADK chat stays optional for engineers. Contract: `Phase0Result` |

### Decisions locked

| # | Decision | Choice |
|---|----------|--------|
| 1 | First-run IA | **1A** — collapsed first-run; hide empty Held/Watched shells until first ticker |
| 7 | Portfolio UI placement | **7A** — same shell; `Watchlist \| Risk` text nav; shared DESIGN.md tokens |

---

## Interaction states

**States score:** 10/10 (decision 2C locked 2026-07-28)

What the user **sees** (not backend behavior).

| FEATURE | LOADING | EMPTY | ERROR | SUCCESS | PARTIAL |
|---------|---------|-------|-------|---------|---------|
| Watchlist page load | Soft line under toolbar: “Loading watchlist…” — no table chrome | **First-run (0 tickers):** collapsed 1A composition. Tagline: “Add a ticker to start grounded research.” Form focused. No section headers. | Banner under toolbar (`role="alert"`): plain-language failure + “Retry” that reloads list. Keep form usable. | Held then Watched sections with rows; Refresh all visible | N/A at page level |
| Held / Watched section | — | **Sibling empty (other list has rows):** warm one-liner + inline cue to add into this list, e.g. Held empty: “Nothing held yet. Add a ticker as Held when you own it.” Primary action remains the toolbar form (preselect list kind on that CTA if easy). | — | Table of rows | — |
| Add ticker | Inputs + Add disabled; button label “Adding…” | — | Banner: invalid ticker / API failure. Form keeps the typed value. | Form clears; new row appears in the right section; that row enters refreshing state | — |
| Row refresh | Status pulse; Refresh button shows “…”; row stays selectable | — | Banner + row keeps last known summary (don’t blank the row) | Summary cells update; if detail open for that ticker, detail reloads | Status badge `partial` in copper/gold; thesis/conflict cells may show gaps as “—” |
| Refresh all | Toolbar button disabled + label “Refreshing…”; optional muted line “Refreshing N tickers…” | Disabled / hidden on first-run | Banner; lists keep prior data | All summaries refresh | Some rows `ok`, some `partial`/`error` — each row honest |
| Detail panel | “Loading research…” in panel body; ticker header may show selected symbol from row | Section empties: see below | Panel shows error message; Close still works. No fake scorecard. | Full hierarchy (status → scorecard → thesis → conflicts → fundamentals) | Status badge `partial`; missing fields as “—”; thesis may be absent with warm gap copy |
| Scorecard (detail) | — | “Scores unavailable for this run.” One line why if `error_message` present. No fake zeros. | — | Dimension grid with 0–100 or “—” per dim | Some dims “—”, others filled |
| Thesis (detail) | — | “No cited thesis for this run.” If status error/partial, one line pointing at honesty (gaps/conflicts), not a CTA to “generate” | — | Summary + claim list with evidence IDs | Thesis present but conflicts listed below — conflicts stay visible |
| Conflicts (detail) | — | Calm success copy: “No source conflicts detected.” (agreement is good, not an empty failure) | — | List by topic + severity + summary | — |
| Fundamentals (detail) | — | “No fundamentals in this result.” | — | Key metrics grid | Sparse metrics + “—” |
| Remove ticker | — | — | Banner if remove fails; ticker stays | Row gone; if it was selected, panel closes | — |
| **Brief page** | Soft line: “Generating today’s brief…”; prior Brief stays visible if any | **No universe:** “Add tickers on Watchlist to generate a Brief.” **No material events:** calm “Nothing material in the last 24h.” | Banner + Retry Generate; keep last Brief if present | Triage dashboard: High/Medium/Quiet sections of ranked ticker **rows** (cap 15); Impact Score; bullets with optional source links; digest strip; timeline; provider-labeled insights | `generation_status` stale/partial banner; per-row `partial`/`unavailable` honest |
| Brief Generate | Button “Generating…”; disabled until done | — | Banner; do not invent bullets | New Brief replaces prior; date/meta updates | Some tickers unavailable — omit quiet; show unavailable only when move unknown and no bullets |

### Empty-state copy principles

1. Warmth: one human sentence, no “No items found.”
2. Primary action: point at Add (or list-kind) — except conflict-empty, which is success.
3. Context: say *why* it matters (held vs watched, cited thesis, honest gaps).

### Decisions locked (states)

| # | Decision | Choice |
|---|----------|--------|
| 2 | Remove confirm | **2C** — instant remove for Held and Watched; no confirm dialog (dogfood speed; re-add is cheap) |

---

## User journey & emotional arc

**Journey score:** 10/10 (decision 3A locked 2026-07-28)

### Time horizons

| Horizon | Goal | How the UI supports it |
|---------|------|------------------------|
| **5 seconds** (visceral) | “This is a serious research tool, not a toy chatbot.” | Fraunces brand, paper/navy, copper accent, calm density — no purple SaaS cards |
| **5 minutes** (behavioral) | Add a name, refresh, open detail, trust status/conflicts | Fast add → row → detail; honest `ok`/`partial`/`error`; conflicts visible |
| **5 years** (reflective) | “I can verify what FolioTracker said.” | Evidence IDs on claims, disclaimer always on, no fake buy/trim signals |

### Storyboard — core dogfood loop

| STEP | USER DOES | USER FEELS | PLAN SPECIFIES? |
|------|-----------|------------|-----------------|
| 1 | Lands on empty app | Oriented, invited — not abandoned | **1A** collapsed first-run; warm tagline; add form is the only workspace control |
| 2 | Types ticker, picks Watched/Held, Add | In control; brief wait is OK | Adding… disabled state; form clears on success |
| 3 | Sees new row while research runs | Anticipation, not anxiety | Row refreshing pulse; last cells may be “—” until done |
| 4 | Row settles: status + G/V/R + thesis one-liner | Glanceable payoff | ScoreStrip; status color; thesis truncation |
| 5 | Opens detail | Deeper trust or productive doubt | Panel hierarchy; conflicts as trust feature |
| 6 | Notices `partial` or conflicts | Respect — product didn’t paper over gaps | Badge + ConflictsList; no auto advice |
| 7 | Refresh later / add more names | Habit forming | Refresh all; Held before Watched |
| 8 | Removes a mistake ticker | Mild friction only | **2C** instant remove; re-add cheap |

### Emotional risks (mitigations)

- **First research feels slow** → **3A + eng E1/1A:** row stays; static muted line describing the research job (not rotating fake stages). `aria-live="polite"`. No determinate progress bar.
- **Partial looks like failure** → status label stays `partial` in copper; utility copy never says “failed” for partial.
- **Thesis absent on error** → warm gap copy from states table; no “generate again” CTA that implies inventing claims.

### Decisions locked (journey)

| # | Decision | Choice |
|---|----------|--------|
| 3 | First-research wait | **3A** — keep row; muted honest stage line; no progress bar |

---

## AI slop risk

**Classifier:** APP UI  
**Slop score:** 10/10 (decision 4A locked 2026-07-28)

### Litmus (current shipped UI)

| Check | Pass? |
|-------|-------|
| Brand/product unmistakable in first screen? | YES — FolioTracker display type |
| One strong visual anchor? | YES — brand wordmark as hero type |
| Page understandable by scanning headlines only? | YES — Held / Watched |
| Each section has one job? | YES |
| Are cards actually necessary? | YES — none in hero; table is the workspace (not a card mosaic) |
| Does motion improve hierarchy? | YES — row rise stagger, panel slide, refresh pulse |
| Premium without decorative shadows? | MOSTLY — one panel shadow; acceptable for overlay depth |

### Hard rejection scan

| Pattern | Present? | Action |
|---------|----------|--------|
| Generic SaaS card grid as first impression | No | — |
| Beautiful image / weak brand | No | — |
| Strong headline, no action | No (add form) | — |
| Busy imagery behind text | No (subtle paper grain only) | — |
| App UI of stacked decorative cards | No | — |
| Purple/indigo gradient theme | No | — |
| 3-column feature grid | No | — |
| Icons in colored circles | No | — |
| Centered everything | No | — |
| Emoji as design | No | — |
| **Colored left-border on conflict cards** | **YES** (`ConflictsList.svelte`) | Replace — see Issue 4 |
| Generic hero copy (“Welcome…”, “Unlock…”) | No — utility tagline | Keep utility language |

### Intentional visual system (keep)

- CSS vars: `--ink`, `--paper`, `--accent` (copper `#c45c26`), status greens/golds/reds
- Type: Fraunces display + IBM Plex Sans body (not Inter/Roboto/system)
- Density: table workspace, minimal chrome, sharp 2px radii
- Motion: 2–3 intentional (row enter, panel slide, refresh pulse)

### Decisions locked (slop)

| # | Decision | Choice |
|---|----------|--------|
| 4 | Conflict list chrome | **4A** — no left border; topic strong type, severity small uppercase meta, summary soft ink |

---

## Design system alignment

**System score:** 10/10 (decision 5A locked 2026-07-28 — lean `DESIGN.md` written)

### Current state

| Artifact | Status |
|----------|--------|
| `DESIGN.md` (repo root) | **Present** (lean lock, 5A) |
| Token source of truth | `web/src/app.css` `:root` vars (mirrored in DESIGN.md) |
| This plan | Product UX decisions; DESIGN.md is the durable system summary |

### Tokens to treat as canonical (from shipped CSS)

| Token | Value | Role |
|-------|-------|------|
| `--ink` | `#0c1b2a` | Primary text / navy |
| `--ink-soft` | `#1a3348` | Secondary text |
| `--paper` | `#f4f7f2` | Page ground |
| `--paper-deep` | `#e7eee4` | Subtle depth |
| `--accent` | `#c45c26` | Copper accent (selection, focus, emphasis) |
| `--accent-soft` | copper @ 12% | Row hover / selected |
| `--ok` / `--partial` / `--error` | green / gold / red | Status honesty |
| `--font-display` | Fraunces | Brand, tickers, section titles |
| `--font-body` | IBM Plex Sans | UI chrome, tables, body |
| Radius | `2px` | Sharp, tool-like — not bubbly |
| Focus | `2px solid var(--accent)` | `:focus-visible` |

### Component vocabulary (shipped — reuse)

`WatchlistPage` · `AddTickerForm` · `TickerListSection` · `TickerRow` · `ScoreStrip` · `TickerDetailPanel` · `ConflictsList` · `TickerIntakePanel` · `DisclaimerBar` · `PrimaryNav` · `RiskPage` · `BriefPage` + `brief/*` (`PrioritySection`, `EventRow`, `FilterBar`, `PortfolioSummary`, `TimelineRail`, `HeatMap`, `StockDrawer`, `SourceList`)

The planned `ThesisPage` + `thesis/*` components must extend this vocabulary and the same visual language — not invent a second one. Shipped `brief/*` components are the Engine 1 surface and stay unchanged.

### Decisions locked (system)

| # | Decision | Choice |
|---|----------|--------|
| 5 | Design system home | **5A** — lean [`DESIGN.md`](../DESIGN.md) from shipped CSS + this plan |

---

## Responsive & accessibility

**Responsive/a11y score:** 10/10 (decision 6A locked 2026-07-28)

### Viewports (intentional — not “stack on mobile”)

| Viewport | Layout |
|----------|--------|
| **≥960px** | Max-width ~1100px page; full table columns; detail panel fixed right `min(28rem, 100%)` |
| **640–959px** | Keep table with horizontal scroll inside `.table-wrap` (dense data stays tabular). Toolbar wraps. Detail panel still right sheet; may cover more of the list — OK. |
| **<640px** | **List, not tiny table:** each ticker becomes a block row — ticker + status on line 1; G/V/R + Fwd P/E on line 2; thesis one-liner on line 3; actions on line 4. Held/Watched section headers stay. Detail panel becomes **full-viewport sheet** (same hierarchy). First-run 1A unchanged (already single column). |

Do not hide Held/Watched labels on mobile. Do not switch to a card mosaic with icons.

### Keyboard

| Control | Behavior |
|---------|----------|
| Tab | Form controls, Refresh all, each row (`tabindex=0`), row action buttons, detail Close |
| Enter / Space on row | Open detail |
| Escape | Close detail panel; return focus to the row that opened it |
| Focus on open | Move focus to panel heading or Close control |
| Focus trap | Required on &lt;640px full-viewport sheet; desktop right panel: trap recommended when open |
| Row actions | Buttons remain in tab order; click/activate does not open detail (stopPropagation stays) |

### Screen reader / structure

- Page: one `main` landmark wrapping watchlist content; disclaimer as `role="note"` (already).
- Detail: `aside` with `aria-label="Ticker detail"`; when open, consider `aria-modal` or focus trap lite (focus moves to Close or panel heading on open).
- Live updates: refresh/error banners use `role="alert"`; researching stage line uses `aria-live="polite"`.
- Status: text label always (`ok` / `partial` / `error`), not color alone.

### Touch & contrast

- Minimum tap target **44×44px** for Add, Refresh, Remove, Close, and row action hit areas (padding OK to reach size).
- Body text on paper: ink on paper meets contrast; keep status colors on text labels (not color-only chips without text).
- Focus: existing copper `:focus-visible` — do not remove.

### Decisions locked (responsive)

| # | Decision | Choice |
|---|----------|--------|
| 6 | Mobile list | **6A** — &lt;640px block rows + full-viewport detail sheet; desktop/tablet table retained |

---

## Unresolved design decisions

| DECISION NEEDED | IF DEFERRED, WHAT HAPPENS |
|-----------------|---------------------------|
| — | None open from this review |

### Locked this review

| # | Decision | Choice |
|---|----------|--------|
| 1 | First-run IA | **1A** |
| 2 | Remove confirm | **2C** |
| 3 | Research wait | **3A** |
| 4 | Conflicts chrome | **4A** |
| 5 | DESIGN.md | **5A** |
| 6 | Mobile list | **6A** |
| 7 | Portfolio surface | **7A** — Watchlist \| Risk in same shell |
| 8 | Phase 3 research UI | **8A** — deepen detail panel; optional full-page; no parallel chat UI |
| 9 | Detail focus | **Obvious fix:** on open, move focus to panel heading/Close; Escape closes + returns focus to row; on &lt;640px full sheet use focus trap so Tab stays in panel |

### Deferred intentionally (NOT in scope for v1 polish)

| Item | Rationale |
|------|-----------|
| Dark mode | Dogfood light paper system only; no second palette |
| Marketing landing page | Product is app UI; no public marketing surface yet |
| Portfolio correlation visuals (charts) | Risk v2 ships text tables only; charts stay deferred |
| Multi-brand / theming | Single product identity |
| Illustration / icon system | Utility app; no icon circles |
| Undo toast for remove | **2C** chose instant remove; revisit only if dogfood regrets pile up |

### What already exists (reuse)

- [`DESIGN.md`](../DESIGN.md) — tokens, type, voice, component vocabulary
- `web/src/app.css` — CSS variables + paper atmosphere
- Components: `WatchlistPage`, `AddTickerForm`, `TickerRow`, `ScoreStrip`, `TickerDetailPanel`, `ConflictsList`, `DisclaimerBar`
- Contract: render `Phase0Result` only — never invent metrics
- Prior locks: navy/paper/copper; Fraunces + IBM Plex Sans

### Pass 7 complete

All design choices from this review are locked (1–8 + focus management). Implementation polish tracked via TODOS.

**TODOS accepted this review:** First-run + warm empty lists (P1); Research wait stage line (P1); Conflicts list chrome (P2); Mobile layout + keyboard/a11y (P1); Interaction-state copy pass (P2).

---

## Design review completion

| Pass | Before → After |
|------|----------------|
| Info Arch | 6 → 10 |
| States | 4 → 10 |
| Journey | 5 → 10 |
| AI Slop | 7 → 10 |
| Design System | 4 → 10 |
| Responsive/a11y | 3 → 10 |
| Decisions | 8 locked, 0 open |

**Overall design score:** 5/10 → 9/10 (plan complete; implementation still in TODOS)

Risk nav scaffold + correlation table shipped (Risk v2, 2026-07-31). **Daily Decision Brief Slice 1 shipped** (2026-08-03) and **triage dashboard shipped** (2026-08-04) — nav is `Watchlist | Risk | Brief`. **Flexible ticker intake shipped** (2026-08-03). Further TODOS: Brief dogfood Assignment, **Thesis landing page T1–T5** (next planned surface), Phase 3 evidence deepen, server single-flight.

### Brief surface (office-hours 2026-07-31 — Approach B; triage dashboard shipped 2026-08-04)

**This is the Engine 1 (Market Intelligence) surface of Portfolio Intelligence — preserved unchanged** ([PRD §1.2](PRD.md)). Shipped beyond Slice 1: High/Medium/Quiet priority sections with Impact Score, filters, morning digest strip, history timeline, heat map, stock drawer, and provider-labeled insight blocks (`BRIEF_INSIGHT_MODE`). The only queued visual change is the additive Brief E1 morning count strip (after Thesis T3).

Constraint worship — if the user can only notice **3 things** on Brief:

1. **Brand + date** — FolioTracker + which Brief day / how many tickers surfaced  
2. **Generate today** — primary action (cache-first)  
3. **Ranked material rows** — High/Medium/Quiet triage, move + precise bullets + optional source links  

Secondary: metrics strip, digest strip, timeline, heat map, miss log, disclaimer, Phase-next social placeholder.

Wireframe: `~/.gstack/projects/schohan-foliotracker/brief-wireframe-20260731.html`

### Thesis surface (planned — Portfolio Intelligence, Engines 2–6)

New landing page beside Brief (`PrimaryNav`: Watchlist | Risk | Brief | **Thesis**), replacing the embedded thesis surface (Watchlist one-liner + detail-panel text). Product contract: [PRD §5.4](PRD.md) normative examples; system contracts: [architecture.md](architecture.md) Thesis section. **Detailed design pass happens at T1 — nothing below is a locked wireframe.** Design intents to carry in:

1. **Same visual language** — navy/paper/copper, Fraunces + IBM Plex Sans, table-first density; `thesis/*` components extend the shipped vocabulary (no second design system).
2. **Constraint worship (provisional 3 things):** framework score table (every holding × multiple philosophies) · thesis-change verdicts · Generate/refresh action. Secondary: valuation ladder, net-asset breakdown, Margin of Safety visualization, portfolio rollup, AI Research button.
3. **Honesty patterns reused:** `null`/"insufficient data" gaps rendered as "—" (never invented values); provider labels on every insight (`THESIS_INSIGHT_MODE` mirrors Brief); disclaimer always visible.
4. **Directive phrasing is visually scoped:** buy/hold/trim/research language appears **only** inside the Advisor insight block (with reasoning + confidence) — no directive copy leaks into score tables, valuations, or rollups.
5. **Verdict vocabulary is a closed set:** `No change | Strengthened | Slightly weaker | Broken` — styled as status labels (text + color, like ok/partial/error), not free prose.

### Eng review scope (2026-07-28) — **A locked**

Implement the 5 watchlist polish TODOs in one UI-focused PR:

- Client-timed research stage copy (no SSE / stage API)
- Add Vitest for critical UI logic (stage helper, empty-state matrix helpers)
- **NOT in scope (polish PR):** streaming stages, Risk nav scaffold, portfolio schemas, Phase 3 evidence browser deepen (Risk v1 landed later)

```
POLISH DATA FLOW (scope A)
==========================
[Browser] WatchlistPage
    │ add / refresh / remove
    ▼
[Vite proxy] /api/* ──► FastAPI (unchanged contract)
    │                         │
    │                         ▼
    │                   run_phase0_research (blocking)
    │                         │
    ▼                         ▼
row.refreshing=true     Phase0Result / summary JSON
stage line (client)           │
    │                         ▼
    └──────────── UI updates ◄┘
```

Pure helpers to extract (testable): `listVisibility()`, research wait copy helper, optional `trapFocus()`.

### Eng decisions locked

| # | Section | Choice |
|---|---------|--------|
| Scope | Step 0 | **A** — 5 polish TODOs, UI-only, Vitest for helpers |
| E1 | Architecture | **1A** — static honest wait copy (describe the job, not fake pipeline step) |
| E2 | Code quality | **2A** — extract `TickerListSection.svelte` + `listVisibility()` |
| E3 | Tests | **3A** — Vitest helpers + manual QA checklist; no Playwright in this PR |
| E4 | Performance | **4A** — UI single-flight: defer detail `fetchResearch` while `refreshing[ticker]` |
| E4b | Outside voice | **Accepted** — extend 4A: `onRefreshAll` must set `refreshing[t]=true` for each batch target so detail cannot double-fetch mid-batch |
| E5 | Outside voice | **Accepted** — Add is membership-first: POST add, clear form, set `refreshing[ticker]`, await refresh in background; do not hold global `busy` for the full Phase0 run |
| E6 | Outside voice | **Accepted** — Error banner Retry is P1 (T2b), not buried in P2 copy |

**Outside voice (acknowledged, no plan change):** Mobile T3 is a second row renderer (effort risk); Vitest-only is intentional 3A; server single-flight already in TODOS; polish-vs-portfolio is intentional dogfood sequence.

**Code quality:** no further issues — delete no-op `sectionRows` during extract; keep Vitest on pure helpers only (not full component mount suite in v1).

### Eng test plan (Section 3)

**Framework:** add Vitest + `npm test` in `web/` (none today). Python API tests already cover watchlist store/service/API — do not re-test those in this PR.

```
WATCHLIST POLISH — CODEPATH COVERAGE
====================================
[+] listVisibility(heldCount, watchedCount)
    ├── [★★★ PLAN] 0,0 → first-run
    ├── [★★★ PLAN] >0,0 → held only (+ watched empty sibling)
    ├── [★★★ PLAN] 0,>0 → watched only (+ held empty sibling)
    └── [★★★ PLAN] >0,>0 → both populated

[+] researchWaitCopy(isRefreshing)
    ├── [★★  PLAN] false → null/empty
    └── [★★  PLAN] true → static honest line (E1/1A)

[+] TickerListSection (via helpers + light render if cheap)
    ├── [★★  PLAN] empty copy props render path [unit]
    └── [→E2E optional] full first-run → add → row appears

[+] Focus / Escape
    ├── [★★  PLAN] pure: shouldCloseOnEscape(key) / focus return target id
    └── [GAP] full focus-trap DOM — hard in unit; [→manual] or later E2E

[+] ConflictsList chrome
    └── [★   PLAN] optional snapshot/class assertion — low value; CSS review OK

USER FLOWS
----------
1. First-run → Add ticker → row refreshing + wait copy → summary fills
2. One-sided empty sibling shows warm CTA copy
3. Open detail → Escape closes → focus returns [→manual / later E2E]
4. Error banner → Retry reloads list
5. Double-click Add while busy → ignored (disabled)

API (existing — do not expand in polish PR)
-------------------------------------------
[+] test_api_watchlist / test_watchlist_service / test_watchlist_store ★★★ already
```

**Tests locked:** **3A** — Vitest for `listVisibility` / wait-copy / Escape helper; PR description includes manual checklist for first-run, Escape, mobile sheet. Playwright deferred.

**Performance:** no further polish issues. `refresh_batch` already caps workers/tickers. Server single-flight deferred.

### Failure modes (polish paths)

| Path | Failure | Test? | User sees? |
|------|---------|-------|------------|
| listVisibility wrong | First-run shows empty shells | ★★★ Vitest | Empty spreadsheet — covered |
| Wait copy missing | Silent pulse only | ★★ Vitest | Mild confusion — covered |
| Double research | Two Phase0 runs | **4A** guard | Slow/costly — mitigated |
| Escape broken | Focus stuck in sheet | Manual checklist | Stuck panel — checklist |
| Refresh fails mid-wait | Row stuck refreshing | Existing error banner | Banner — exists |
| Add while busy | Double membership | Button disabled | Ignored — exists |

**Critical gaps:** 0 (with 4A + Vitest + manual Escape checklist).

### NOT in scope (eng)

| Item | Rationale |
|------|-----------|
| SSE / streaming research stages | Scope A; honesty via static copy (E1) |
| Server Phase0 single-flight | 4B deferred; UI guard enough for dogfood |
| Playwright E2E | 3B deferred |
| Watchlist \| Risk nav scaffold | **Done** Risk v1 (2026-07-30) |
| Phase 3 evidence browser deepen | Separate Phase 3 lock (design 8A); queued in TODOS |

### What already exists (reuse)

| Existing | Reuse? |
|----------|--------|
| FastAPI watchlist + `run_phase0_research` | Yes — unchanged contracts |
| `WatchlistPage` / rows / detail / conflicts | Yes — polish in place |
| pytest `test_api_watchlist*` | Yes — no reimplementation |
| Vite `/api` proxy | Yes |
| DESIGN.md + design-plan decisions 1–8 | Yes — implementation source |

### Worktree parallelization

Sequential implementation, no parallelization opportunity — all polish touches `web/src` (same module). One PR lane.

## Implementation Tasks

Synthesized from this eng review. Checkbox as you ship.

- [x] **T1 (P1, human: ~2h / CC: ~30min)** — Extract `TickerListSection` + `listVisibility` + first-run / warm empties
  - Surfaced by: Code quality 2A + design 1A
  - Files: `web/src/lib/components/WatchlistPage.svelte`, `TickerListSection.svelte`, `web/src/lib/listVisibility.ts`
  - Verify: `npm test` listVisibility cases; manual first-run
- [x] **T2 (P1, human: ~1.5h / CC: ~30min)** — Static wait copy + UI single-flight (per-row + refresh-all) + membership-first Add (background refresh)
  - Surfaced by: E1/1A + E4/4A + outside voice refresh-all + add-busy
  - Files: `WatchlistPage.svelte`, `TickerRow.svelte`, `web/src/lib/researchWaitCopy.ts`
  - Verify: Vitest wait-copy; add second ticker while first researches; open detail during refresh-all does not double-fetch
- [x] **T2b (P1, human: ~30min / CC: ~10min)** — Error banner **Retry** control (calls `load()` / reload watchlist)
  - Surfaced by: Design states table + outside voice (Retry buried in P2)
  - Files: `WatchlistPage.svelte`
  - Verify: Manual — kill API, see banner + Retry recovers
- [x] **T3 (P1, human: ~1d / CC: ~1h)** — Mobile block rows + Escape/focus trap + 44px targets
  - Surfaced by: Design 6A + eng a11y
  - Files: `TickerListSection.svelte`, `TickerDetailPanel.svelte`, `app.css`
  - Verify: Manual checklist &lt;640px + Escape
- [x] **T4 (P2, human: ~45min / CC: ~15min)** — ConflictsList chrome + interaction-state copy
  - Surfaced by: Design 4A + copy TODO
  - Files: `ConflictsList.svelte`, `TickerDetailPanel.svelte`, `AddTickerForm.svelte`
  - Verify: Visual + copy spot-check
- [x] **T5 (P1, human: ~1h / CC: ~20min)** — Add Vitest harness + helper tests + PR manual QA checklist
  - Surfaced by: Tests 3A
  - Files: `web/package.json`, `web/vitest.config.ts`, `web/src/lib/*.test.ts`
  - Verify: `cd web && npm test`

### Eng review completion

| Item | Result |
|------|--------|
| Step 0 | Scope **A** accepted (UI polish + Vitest; no SSE) — SCOPE_REDUCED vs streaming |
| Architecture | 1 issue → **1A** static wait copy |
| Code quality | 1 issue → **2A** TickerListSection extract |
| Tests | diagram + **3A** Vitest + manual checklist |
| Performance | 1 issue → **4A** + **E4b** refresh-all flags |
| Outside voice | 3 tensions accepted (refresh-all, membership-first Add, Retry P1) |
| NOT in scope | written |
| What already exists | written |
| TODOS | Playwright skipped; Phase0 single-flight **added** |
| Failure modes | 0 critical gaps |
| Parallelization | Sequential (`web/`) |
| Lake score | 6/6 complete options chosen on coverage questions |

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 0 | — | — |
| Codex Review | `/codex review` | Independent 2nd opinion | 0 | — | — (outside voice via Claude subagent; Codex CLI not installed) |
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 2 | CLEAR (PLAN) | 7 issues, 0 critical gaps; SCOPE_REDUCED polish |
| Design Review | `/plan-design-review` | UI/UX gaps | 1 | CLEAR (FULL) | score: 5/10 → 9/10, 8 decisions |
| DX Review | `/plan-devex-review` | Developer experience gaps | 0 | — | — |

**VERDICT:** ENG + DESIGN CLEARED — ready to implement watchlist polish tasks T1–T5.

NO UNRESOLVED DECISIONS

