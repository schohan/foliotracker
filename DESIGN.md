# FolioTracker Design System

**Status:** Lean lock from shipped watchlist v1 + `/plan-design-review` (2026-07-28)  
**Source of truth for tokens in code:** `web/src/app.css`  
**Product UX decisions:** [docs/design-plan.md](docs/design-plan.md)

Classifier: **App UI** — dense research workspace, not a marketing site.

---

## Brand & voice

- **Brand first:** “FolioTracker” in Fraunces is the loudest text on the watchlist.
- **Utility copy:** orientation, status, action. Not mood, aspiration, or “Welcome to…”.
- **Trust:** honest `ok` / `partial` / `error`. No auto buy/trim signals. Disclaimer always present.
- **Cite-first:** claims show evidence IDs; conflicts are a feature, not a failure banner.

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

- **Primary workspace:** Held / Watched tables (Held first). Text nav `Watchlist | Risk | Brief` (Brief = daily material-event triage).
- **Secondary context:** Right detail panel on row select (Watchlist only). Brief has no detail panel in Slice 1 — ranked rows only.
- **First-run (0 tickers):** Collapsed composition — brand, one line, add form only. No empty section shells. Brief with empty universe: calm “Add tickers on Watchlist to generate a Brief.”
- **Cards:** Default none. Tables, list rows, and the detail panel are the interaction surfaces. No dashboard card mosaic. Brief uses **ranked ticker rows**, not cards.
- **Radius:** `2px` — tool-like, not bubbly.
- **Motion (intentional):** row enter stagger, detail panel slide, refresh pulse. Brief: Generate pulse only. No ornamental motion.

---

## Components (vocabulary)

Reuse before inventing:

| Component | Job |
|-----------|-----|
| `WatchlistPage` | Page shell, lists, first-run |
| `PrimaryNav` | Text nav `Watchlist \| Risk \| Brief` |
| `RiskPage` | Held equal-weight concentration + top pairwise correlations (tables; no charts) |
| `BriefPage` | Daily Decision Brief — Generate, ranked material rows, miss log (Slice 1) |
| `AddTickerForm` | Primary add action |
| `TickerRow` | Glanceable summary row |
| `ScoreStrip` | G / V / R glance (Brief metrics strip may reuse Growth/Value/Risk only) |
| `TickerDetailPanel` | Deep read of `Phase0Result` |
| `ConflictsList` | Source disagreements (no left-border accent stripe) |
| `DisclaimerBar` | Non-advice, always on |

Portfolio / Brief / Phase 3 UI must extend this vocabulary and these tokens.

**Brief trust rules (UI):** optional source links on bullets; never auto buy/trim; Phase-next social section (if shown) must be visually separate and labeled display-only / not used in scores.

---

## Interaction rules (summary)

Full state table: [docs/design-plan.md](docs/design-plan.md#interaction-states).

- Empty states: warmth + primary action + context (except conflict-empty = calm success).
- Research wait: keep row; muted honest stage line (no fake progress bar).
- Remove: instant (no confirm) for Held and Watched.
- Detail hierarchy: status → scorecard → thesis → conflicts → fundamentals → raw JSON.
- Brief: whole-Brief empty when no ticker passes the material gate; quiet names omitted (not listed empty); stale/partial Generate uses banner via `generation_status`.

---

## Accessibility (minimum)

- `:focus-visible` with copper outline.
- Status and errors not by color alone (text labels: ok / partial / error).
- Detail panel has accessible name; Close has `aria-label`.
- Touch targets and responsive behavior: see design-plan Pass 6.

---

## Out of scope for this doc

Marketing landing page rules, illustration system, dark mode, multi-brand theming.
