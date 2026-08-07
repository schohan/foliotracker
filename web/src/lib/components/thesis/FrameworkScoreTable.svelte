<script lang="ts">
  import { formatFrameworkScore } from "../../thesisFormat";
  import type { FrameworkId, ThesisTicker } from "../../types";

  interface Props {
    tickers: ThesisTicker[];
    frameworks: FrameworkId[];
    selected: string | null;
    onselect: (ticker: string) => void;
  }

  let { tickers, frameworks, selected, onselect }: Props = $props();

  const labels: Record<FrameworkId, string> = {
    graham: "Graham Deep Value",
    financial_strength: "Financial Strength",
  };

  function scoreFor(row: ThesisTicker, framework: FrameworkId): number | null {
    return row.frameworks.find((f) => f.framework === framework)?.score ?? null;
  }
</script>

<table>
  <thead>
    <tr>
      <th scope="col">Ticker</th>
      <th scope="col">List</th>
      <th scope="col">Sector</th>
      {#each frameworks as fw (fw)}
        <th scope="col" class="score-col">{labels[fw]}</th>
      {/each}
    </tr>
  </thead>
  <tbody>
    {#each tickers as row (row.ticker)}
      <tr
        class:selected={selected === row.ticker}
        onclick={() => onselect(row.ticker)}
      >
        <td class="ticker">
          <button type="button" class="row-btn" onclick={() => onselect(row.ticker)}>
            {row.ticker}
          </button>
        </td>
        <td class="muted">{row.list_kind}</td>
        <td class="muted">{row.sector ?? "—"}</td>
        {#each frameworks as fw (fw)}
          {@const score = scoreFor(row, fw)}
          <td class="score-col score" class:na={score == null}>
            {formatFrameworkScore(score)}
          </td>
        {/each}
      </tr>
    {/each}
  </tbody>
</table>

<style>
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
  }
  th {
    color: var(--ink-soft);
    font-weight: 500;
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }
  tr {
    cursor: pointer;
  }
  tr.selected {
    background: rgba(0, 0, 0, 0.04);
  }
  .ticker {
    font-family: var(--font-display);
    font-weight: 600;
  }
  .row-btn {
    border: none;
    background: transparent;
    font: inherit;
    color: inherit;
    padding: 0;
    min-height: 44px;
    cursor: pointer;
  }
  .muted {
    color: var(--ink-soft);
  }
  .score-col {
    text-align: right;
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
</style>
