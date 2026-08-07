<script lang="ts">
  import { rowFocusId } from "../../focusHelpers";
  import { formatFrameworkScore, thesisRowCoverage } from "../../thesisFormat";
  import type { FrameworkId, ThesisTicker } from "../../types";

  interface Props {
    tickers: ThesisTicker[];
    frameworks: FrameworkId[];
    selected: string | null;
    onselect: (ticker: string) => void;
  }

  let { tickers, frameworks, selected, onselect }: Props = $props();

  const labels: Record<FrameworkId, string> = {
    graham: "Graham",
    financial_strength: "Fin. Strength",
  };

  function scoreFor(row: ThesisTicker, framework: FrameworkId): number | null {
    return row.frameworks.find((f) => f.framework === framework)?.score ?? null;
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
</script>

<div class="table-wrap">
  <table>
    <thead>
      <tr>
        <th scope="col">Ticker</th>
        <th scope="col">List</th>
        <th scope="col">Data</th>
        <th scope="col">Sector</th>
        {#each frameworks as fw (fw)}
          <th scope="col" class="score-col">{labels[fw]}</th>
        {/each}
        <th scope="col" class="score-col">OS</th>
      </tr>
    </thead>
    <tbody>
      {#each tickers as row (row.ticker)}
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
    </tbody>
  </table>
</div>

<p class="cue" aria-live="polite">
  {#if selected}
    Viewing {selected} — detail opens on the right. Esc closes.
  {:else}
    Select a row for frameworks, valuation, thesis change, and advisor.
  {/if}
</p>

<style>
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
    padding: 0.6rem 0.45rem;
    border-bottom: 1px solid var(--line);
    vertical-align: middle;
  }
  th {
    color: var(--ink-soft);
    font-weight: 500;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
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
  .score-col {
    text-align: right;
    font-variant-numeric: tabular-nums;
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
