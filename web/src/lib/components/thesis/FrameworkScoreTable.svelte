<script lang="ts">
  import { rowFocusId } from "../../focusHelpers";
  import { formatFrameworkScore, thesisRowCoverage } from "../../thesisFormat";
  import { TABLE_COLUMN_HELP } from "../../thesisHelp";
  import type { FrameworkId, ThesisTicker } from "../../types";
  import HelpTip from "./HelpTip.svelte";

  type SortKey =
    | "ticker"
    | "list"
    | "data"
    | "sector"
    | "os"
    | FrameworkId;

  interface Props {
    tickers: ThesisTicker[];
    frameworks: FrameworkId[];
    selected: string | null;
    /** When set, only these tickers are shown (portfolio health filter). */
    filterTickers?: string[] | null;
    filterLabel?: string | null;
    onselect: (ticker: string) => void;
    onclearfilter?: () => void;
  }

  let {
    tickers,
    frameworks,
    selected,
    filterTickers = null,
    filterLabel = null,
    onselect,
    onclearfilter,
  }: Props = $props();

  let sortKey = $state<SortKey>("ticker");
  let sortDir = $state<"asc" | "desc">("asc");

  const labels: Record<FrameworkId, string> = {
    graham: "Graham",
    financial_strength: "Fin. Strength",
  };

  function scoreFor(row: ThesisTicker, framework: FrameworkId): number | null {
    return row.frameworks.find((f) => f.framework === framework)?.score ?? null;
  }

  function coverageRank(row: ThesisTicker): number {
    const k = thesisRowCoverage(row).kind;
    if (k === "ok") return 2;
    if (k === "partial") return 1;
    return 0;
  }

  function sortValue(row: ThesisTicker, key: SortKey): string | number | null {
    if (key === "ticker") return row.ticker;
    if (key === "list") return row.list_kind;
    if (key === "data") return coverageRank(row);
    if (key === "sector") return (row.sector ?? "").toLowerCase();
    if (key === "os") return row.os_score?.score ?? null;
    if (key === "graham" || key === "financial_strength") {
      return scoreFor(row, key);
    }
    return null;
  }

  function cmp(a: ThesisTicker, b: ThesisTicker): number {
    const av = sortValue(a, sortKey);
    const bv = sortValue(b, sortKey);
    const aNull = av == null || av === "";
    const bNull = bv == null || bv === "";
    if (aNull && bNull) return a.ticker.localeCompare(b.ticker);
    if (aNull) return 1;
    if (bNull) return -1;
    let result = 0;
    if (typeof av === "number" && typeof bv === "number") {
      result = av - bv;
    } else {
      result = String(av).localeCompare(String(bv), undefined, {
        sensitivity: "base",
      });
    }
    if (result === 0) result = a.ticker.localeCompare(b.ticker);
    return sortDir === "asc" ? result : -result;
  }

  const visible = $derived.by(() => {
    const base =
      filterTickers == null
        ? tickers
        : tickers.filter((t) => filterTickers.includes(t.ticker));
    return [...base].sort(cmp);
  });

  function setSort(key: SortKey) {
    if (sortKey === key) {
      sortDir = sortDir === "asc" ? "desc" : "asc";
    } else {
      sortKey = key;
      sortDir = key === "ticker" || key === "list" || key === "sector" ? "asc" : "desc";
    }
  }

  function sortIndicator(key: SortKey): string {
    if (sortKey !== key) return "";
    return sortDir === "asc" ? " ↑" : " ↓";
  }

  function activate(ticker: string) {
    onselect(ticker);
  }

  function onRowKey(e: KeyboardEvent, ticker: string) {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      activate(ticker);
    }
  }

  function colHelp(key: string) {
    return TABLE_COLUMN_HELP[key] ?? TABLE_COLUMN_HELP.ticker;
  }
</script>

{#if filterTickers != null}
  <div class="filter-bar" aria-live="polite">
    <p>
      Filtered to {visible.length} ticker{visible.length === 1 ? "" : "s"}
      {#if filterLabel}
        · {filterLabel}
      {/if}
    </p>
    {#if onclearfilter}
      <button type="button" class="clear" onclick={onclearfilter}>
        Show all
      </button>
    {/if}
  </div>
{/if}

<div class="table-wrap">
  <table>
    <thead>
      <tr>
        <th scope="col" aria-sort={sortKey === "ticker" ? (sortDir === "asc" ? "ascending" : "descending") : "none"}>
          <button type="button" class="sort" onclick={() => setSort("ticker")}>
            Ticker{sortIndicator("ticker")}
          </button>
          <HelpTip entry={colHelp("ticker")} />
        </th>
        <th scope="col" aria-sort={sortKey === "list" ? (sortDir === "asc" ? "ascending" : "descending") : "none"}>
          <button type="button" class="sort" onclick={() => setSort("list")}>
            List{sortIndicator("list")}
          </button>
          <HelpTip entry={colHelp("list")} />
        </th>
        <th scope="col" aria-sort={sortKey === "data" ? (sortDir === "asc" ? "ascending" : "descending") : "none"}>
          <button type="button" class="sort" onclick={() => setSort("data")}>
            Data{sortIndicator("data")}
          </button>
          <HelpTip entry={colHelp("data")} />
        </th>
        <th scope="col" aria-sort={sortKey === "sector" ? (sortDir === "asc" ? "ascending" : "descending") : "none"}>
          <button type="button" class="sort" onclick={() => setSort("sector")}>
            Sector{sortIndicator("sector")}
          </button>
          <HelpTip entry={colHelp("sector")} />
        </th>
        {#each frameworks as fw (fw)}
          <th
            scope="col"
            class="score-col"
            aria-sort={sortKey === fw ? (sortDir === "asc" ? "ascending" : "descending") : "none"}
          >
            <button type="button" class="sort score-sort" onclick={() => setSort(fw)}>
              {labels[fw]}{sortIndicator(fw)}
            </button>
            <HelpTip entry={colHelp(fw)} align="end" />
          </th>
        {/each}
        <th
          scope="col"
          class="score-col"
          aria-sort={sortKey === "os" ? (sortDir === "asc" ? "ascending" : "descending") : "none"}
        >
          <button type="button" class="sort score-sort" onclick={() => setSort("os")}>
            OS{sortIndicator("os")}
          </button>
          <HelpTip entry={colHelp("os")} align="end" />
        </th>
      </tr>
    </thead>
    <tbody>
      {#if visible.length === 0}
        <tr class="empty-row">
          <td colspan={4 + frameworks.length + 1}>No tickers match this filter.</td>
        </tr>
      {:else}
        {#each visible as row (row.ticker)}
          {@const coverage = thesisRowCoverage(row)}
          <tr
            id={rowFocusId(row.ticker)}
            class:selected={selected === row.ticker}
            class:thin={coverage.kind === "thin"}
            tabindex="0"
            aria-selected={selected === row.ticker}
            onclick={() => activate(row.ticker)}
            onkeydown={(e) => onRowKey(e, row.ticker)}
          >
            <td class="ticker">
              <span class="sym">{row.ticker}</span>
              {#if row.name}
                <span class="name">{row.name}</span>
              {/if}
            </td>
            <td class="muted">{row.list_kind}</td>
            <td>
              <span class="cov cov-{coverage.kind}" title={coverage.detail}>
                {coverage.label}
              </span>
            </td>
            <td class="muted">{row.sector ?? "—"}</td>
            {#each frameworks as fw (fw)}
              {@const score = scoreFor(row, fw)}
              <td class="score-col score" class:na={score == null}>
                {formatFrameworkScore(score)}
              </td>
            {/each}
            <td
              class="score-col score"
              class:na={row.os_score?.score == null}
            >
              {formatFrameworkScore(row.os_score?.score ?? null)}
            </td>
          </tr>
        {/each}
      {/if}
    </tbody>
  </table>
</div>

<p class="cue" aria-live="polite">
  {#if selected}
    Viewing {selected} — detail opens on the right. Esc closes.
  {:else}
    Select a row for frameworks, valuation, thesis change, and advisor. Click a
    column header to sort.
  {/if}
</p>

<style>
  .filter-bar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
    margin: 0 0 0.65rem;
    padding: 0.45rem 0.65rem;
    background: var(--accent-soft);
    border-radius: 2px;
    font-size: 0.88rem;
  }
  .filter-bar p {
    margin: 0;
  }
  .clear {
    border: 1px solid var(--line);
    background: white;
    border-radius: 2px;
    padding: 0.3rem 0.6rem;
    min-height: 36px;
    font-weight: 500;
    cursor: pointer;
  }
  .table-wrap {
    overflow-x: auto;
    margin: 0 -0.15rem;
    padding: 0 0.15rem;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.95rem;
  }
  th,
  td {
    text-align: left;
    padding: 0.55rem 0.4rem;
    border-bottom: 1px solid var(--line);
    vertical-align: middle;
  }
  th {
    color: var(--ink-soft);
    font-weight: 500;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    white-space: nowrap;
  }
  .sort {
    appearance: none;
    border: none;
    background: none;
    padding: 0.2rem 0.1rem;
    margin: 0;
    font: inherit;
    color: inherit;
    text-transform: inherit;
    letter-spacing: inherit;
    cursor: pointer;
    min-height: 36px;
  }
  .sort:hover,
  .sort:focus-visible {
    color: var(--accent);
    outline: none;
  }
  .score-sort {
    text-align: right;
  }
  .score-col {
    text-align: right;
    font-variant-numeric: tabular-nums;
  }
  tr {
    cursor: pointer;
    transition: background 0.12s ease;
  }
  tr:hover {
    background: var(--accent-soft);
  }
  tr.selected {
    background: var(--accent-soft);
    box-shadow: inset 3px 0 0 var(--accent);
  }
  tr.thin:not(.selected) td.score.na {
    opacity: 0.75;
  }
  tr:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: -2px;
  }
  .empty-row td {
    color: var(--ink-soft);
    font-style: italic;
    padding: 1rem 0.45rem;
  }
  .ticker {
    font-family: var(--font-display);
    min-width: 6.5rem;
  }
  .sym {
    display: block;
    font-weight: 700;
    letter-spacing: -0.01em;
  }
  .name {
    display: block;
    font-family: var(--font-body, inherit);
    font-weight: 400;
    font-size: 0.78rem;
    color: var(--ink-soft);
    margin-top: 0.1rem;
    max-width: 10rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .muted {
    color: var(--ink-soft);
    text-transform: capitalize;
  }
  .cov {
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: lowercase;
    letter-spacing: 0.02em;
  }
  .cov-ok {
    color: var(--ok);
  }
  .cov-partial {
    color: var(--partial);
  }
  .cov-thin {
    color: var(--error);
  }
  .score {
    font-family: var(--font-display);
    font-weight: 600;
    font-size: 1.05rem;
  }
  .score.na {
    color: var(--ink-soft);
    font-weight: 400;
  }
  .cue {
    margin: 0.65rem 0 0;
    color: var(--ink-soft);
    font-size: 0.85rem;
  }
</style>
