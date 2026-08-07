# FolioTracker Design System

**Status:** Lean lock from shipped watchlist v1 + `/plan-design-review` (2026-07-28)  
**Source of truth for tokens in code:** `web/src/app.css`  
**Product UX decisions:** [docs/design-plan.md](docs/design-plan.md)

Classifier: **App UI** — dense research workspace, not a marketing site.

---

## Brand & voice

- **Brand first:** “FolioTracker” in Fraunces is the loudest text on the watchlist.
- **Utility copy:** orientation, status, action. Not mood, aspiration, or “Welcome to…”.
- **Trust:** honest `ok` / `partial` / `error`. No auto buy/trim signals on Watchlist / Risk / Brief. Disclaimer always present.
- **Scoped exception (2026-08-05):** directive guidance (buy more / hold / trim / research / wait) is allowed **only** from the Thesis page's AI Portfolio Advisor, always with reasoning, confidence, provider label, and disclaimer.
- **Cite-first:** claims show evidence IDs; conflicts are a feature, not a failure banner. Framework scores cite the fundamentals they were computed from.

---

## Color

| Token | Value | Use |
|-------|-------|-----|
| `--ink` | `#0c1b2a` | Primary text, primary buttons |
| `--ink-soft` | `#1a3348` | Secondary text, meta |
| `--paper` | `#f4f7f2` | Page background |
| `--paper-deep` | `#e7eee4` | Subtle depth |
| `--accent` | `#c45c26` | Copper — focus, selection, emphasis (one accent) |
| `--accent-soft` | `rgba(196, 92, 38, 0.12)` | Row hover / selected |
| `--ok` | `#1f7a4c` | Status ok |
| `--partial` | `#b8860b` | Status partial (honest/incomplete, not “broken”) |
| `--error` | `#a32020` | Status error / alerts |
| `--line` | `rgba(12, 27, 42, 0.12)` | Hairlines, table rules |

Atmosphere: soft radial washes + light paper grain on `body`. No purple/indigo gradients. No decorative blob dividers.

---

## Typography

| Role | Family | Notes |
|------|--------|-------|
| Display | **Fraunces** | Brand, section titles, ticker symbols |
| Body | **IBM Plex Sans** | Tables, forms, thesis, chrome |

Do not use Inter, Roboto, Arial, or system-ui as the primary stack. Two typefaces max.

---

## Layout & chrome

- **Primary workspace:** Held / Watched tables (Held first). Text nav `Watchlist | Risk | Brief | Thesis` (Brief = daily material-event triage; Thesis = frameworks + valuation + monitoring, T1–T3 shipped 2026-08-07).
- **Secondary context:** Right detail panel on row select (Watchlist). Brief uses a **StockDrawer** (same fixed-panel pattern) for event + insight drill-down — no full-page navigation away from the triage dashboard.
- **First-run (0 tickers):** Collapsed composition — brand, one line, add form only. No empty section shells. Brief with empty universe: calm “Add tickers on Watchlist to generate a Brief.”
- **Cards:** Default none. Tables, list rows, and the detail panel are the interaction surfaces. No dashboard card mosaic. Brief uses **expandable inbox rows** (Linear-style) plus a portfolio summary strip — not a card grid.
- **Radius:** `2px` — tool-like, not bubbly.
- **Motion (intentional):** row enter stagger, detail panel slide, refresh pulse. Brief: Generate pulse + row expand + drawer slide. No ornamental motion.

---

## Components (vocabulary)

Reuse before inventing:

| Component | Job |
|-----------|-----|
| `WatchlistPage` | Page shell, lists, first-run |
| `PrimaryNav` | Text nav `Watchlist \| Risk \| Brief \| Thesis` |
| `RiskPage` | Held equal-weight concentration + top pairwise correlations (tables; no charts) |
| `BriefPage` | Daily Decision Brief — triage dashboard (summary, filters, High/Medium/Quiet, miss log) |
| `brief/PortfolioSummary` | Holdings counts, themes, morning digest strip |
| `brief/MorningCounts` | E1 Today's Portfolio strip (thesis-backed counts) |
| `brief/FilterBar` | Gmail-like triage filters |
| `brief/EventRow` | Expandable impact-ranked event row |
| `brief/PrioritySection` | High / Medium / Quiet sections |
| `brief/SourceList` | Original source links |
| `brief/HeatMap` | Compact Held/Watched impact grid |
| `brief/TimelineRail` | Brief history browse (ring-14) |
| `brief/StockDrawer` | Side panel for ticker events + insight + research |
| `ThesisPage` | Portfolio Intelligence landing page (T1–T5) — Decision Map + question-headed sections for Engines 2–6 + OS Score + portfolio health |
| `thesis/DecisionMap` | Six PRD decision questions → one-line answers + jump links (Brief / section anchors); Engine 2 stays Planned |
| `thesis/FrameworkScoreTable` | Per-stock scores across investment philosophies + OS Score column |
| `thesis/FrameworkScorecard` | Single-framework drill-down: named checks, PASS/value/rating (T1 shipped) |
| `thesis/ValuationLadder` | Six-value ladder: market / intrinsic / liquidation / replacement / enterprise / expected fair (T2 shipped) |
| `thesis/MarginOfSafety` | Intrinsic vs price, % + star rating (T2 shipped) |
| `thesis/AssetBreakdown` | Net Asset Intelligence: assets − liabilities → adjusted net assets vs market cap (T2 shipped) |
| `thesis/ThesisTimeline` | Quarterly thesis-change verdicts with evidence (T3 shipped) |
| `thesis/AdvisorInsight` | Advisor reasoning + directive conclusion + confidence + provider label (T4 shipped) |
| `thesis/ResearchButton` | One-click framework questions per stock (T4 shipped) |
| `thesis/OSScorecard` | Investment OS Score dimensions + composite (T5 shipped) |
| `thesis/PortfolioHealth` | Portfolio health score + rollup counts (T5 shipped) |
| `AddTickerForm` | Primary add action |
| `TickerRow` | Glanceable summary row |
| `ScoreStrip` | G / V / R glance (Brief metrics strip may reuse Growth/Value/Risk only) |
| `TickerDetailPanel` | Deep read of `Phase0Result` |
| `ConflictsList` | Source disagreements (no left-border accent stripe) |
| `DisclaimerBar` | Non-advice, always on |

Portfolio / Brief / Phase 3 UI must extend this vocabulary and these tokens.

**Brief trust rules (UI):** optional source links on bullets; never auto buy/trim (actions are Read / Review / Monitor); Phase-next social section (if shown) must be visually separate and labeled display-only / not used in scores. Insight `provider` (`deterministic` / `canned` / `llm`) is always visible.

**Thesis trust rules (UI):** directive guidance appears only inside `thesis/AdvisorInsight` (T4), always with reasoning lines, confidence, provider label, and disclaimer. Framework scores and valuations show honest gaps (`null` / “insufficient data”) — never invented values. Thesis reuses the Brief patterns: expandable rows / drawer, no card mosaic, same tokens. Section headings are the PRD decision questions (not “Engine N” chrome); `thesis/DecisionMap` is a denselist strip, not a card grid.

---

## Interaction rules (summary)

Full state table: [docs/design-plan.md](docs/design-plan.md#interaction-states).

- Empty states: warmth + primary action + context (except conflict-empty = calm success).
- Research wait: keep row; muted honest stage line (no fake progress bar).
- Remove: instant (no confirm) for Held and Watched.
- Detail hierarchy: status → scorecard → thesis → conflicts → fundamentals → raw JSON.
- Brief: portfolio summary answers “what requires attention?”; High/Medium ranked by Impact Score; Quiet names listed with ✓; timeline for missed days; `j`/`k` + Enter for keyboard triage; stale/partial Generate uses banner via `generation_status`.

---

## Accessibility (minimum)

- `:focus-visible` with copper outline.
- Status and errors not by color alone (text labels: ok / partial / error).
- Detail panel has accessible name; Close has `aria-label`.
- Touch targets and responsive behavior: see design-plan Pass 6.

---

## Out of scope for this doc

Marketing landing page rules, illustration system, dark mode, multi-brand theming.
