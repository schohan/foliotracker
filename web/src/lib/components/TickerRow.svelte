<script lang="ts">
  import type { WatchlistTickerSummary } from "../types";
  import { researchWaitCopy } from "../researchWaitCopy";
  import { rowFocusId } from "../focusHelpers";
  import ScoreStrip from "./ScoreStrip.svelte";

  interface Props {
    row: WatchlistTickerSummary;
    index: number;
    refreshing?: boolean;
    selected?: boolean;
    onselect: (ticker: string) => void;
    onrefresh: (ticker: string) => void;
    onremove: (ticker: string) => void;
  }
  let {
    row,
    index,
    refreshing = false,
    selected = false,
    onselect,
    onrefresh,
    onremove,
  }: Props = $props();

  const waitLine = $derived(researchWaitCopy(refreshing));
  const focusId = $derived(rowFocusId(row.ticker));

  function onKey(e: KeyboardEvent) {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      onselect(row.ticker);
    }
  }
</script>

<tr
  id={focusId}
  class:selected
  class:refreshing
  style={`--i: ${index}`}
  onclick={() => onselect(row.ticker)}
  onkeydown={onKey}
  tabindex="0"
  aria-selected={selected}
>
  <td class="ticker" data-label="Ticker">{row.ticker}</td>
  <td data-label="Status">
    <span class={`status ${row.status ?? "none"}`}>{row.status ?? "—"}</span>
    {#if waitLine}
      <span class="wait" aria-live="polite">{waitLine}</span>
    {/if}
  </td>
  <td data-label="G / V / R">
    <ScoreStrip
      growth={row.growth_score}
      value={row.value_score}
      risk={row.risk_score}
    />
  </td>
  <td class="num" data-label="Fwd P/E">
    {row.forward_pe == null ? "—" : row.forward_pe.toFixed(1)}
  </td>
  <td class="num" data-label="Conflicts">{row.conflict_count}</td>
  <td class="thesis" data-label="Thesis">
    {row.thesis_one_liner ?? row.error_message ?? "—"}
  </td>
  <td class="meta" data-label="Meta">
    {#if row.cache_hit}
      <span title="Served from cache">cache</span>
    {/if}
    {#if row.request_id}
      <code title={row.request_id}>{row.request_id.slice(0, 8)}</code>
    {/if}
  </td>
  <td class="actions" onclick={(e) => e.stopPropagation()}>
    <button
      type="button"
      class="action"
      disabled={refreshing}
      onclick={() => onrefresh(row.ticker)}
    >
      {refreshing ? "…" : "Refresh"}
    </button>
    <button
      type="button"
      class="action ghost"
      onclick={() => onremove(row.ticker)}
    >
      Remove
    </button>
  </td>
</tr>

<style>
  tr {
    animation: rise 0.35s ease both;
    animation-delay: calc(var(--i) * 40ms);
    border-bottom: 1px solid var(--line);
    cursor: pointer;
  }
  tr:hover,
  tr.selected {
    background: var(--accent-soft);
  }
  tr.refreshing .status {
    animation: pulse 0.9s ease infinite;
  }
  td {
    padding: 0.85rem 0.65rem;
    vertical-align: top;
    font-size: 0.92rem;
  }
  .ticker {
    font-family: var(--font-display);
    font-weight: 700;
    font-size: 1.05rem;
    letter-spacing: 0.02em;
  }
  .status {
    display: inline-block;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }
  .status.ok {
    color: var(--ok);
  }
  .status.partial {
    color: var(--partial);
  }
  .status.error {
    color: var(--error);
  }
  .status.none {
    color: var(--ink-soft);
  }
  .wait {
    display: block;
    margin-top: 0.35rem;
    font-size: 0.78rem;
    font-weight: 400;
    text-transform: none;
    letter-spacing: 0;
    color: var(--ink-soft);
    line-height: 1.35;
    max-width: 14rem;
  }
  .num {
    font-variant-numeric: tabular-nums;
  }
  .thesis {
    max-width: 18rem;
    color: var(--ink-soft);
    line-height: 1.35;
  }
  .meta {
    font-size: 0.75rem;
    color: var(--ink-soft);
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
  }
  code {
    font-size: 0.7rem;
  }
  .actions {
    display: flex;
    gap: 0.35rem;
    white-space: nowrap;
  }
  .action {
    border: 1px solid var(--line);
    background: white;
    padding: 0.45rem 0.7rem;
    min-height: 44px;
    min-width: 44px;
    border-radius: 2px;
    font-size: 0.8rem;
  }
  .action.ghost {
    background: transparent;
  }

  @media (max-width: 639px) {
    td {
      padding: 0.2rem 0;
    }
    .ticker {
      display: inline-block;
      margin-right: 0.65rem;
    }
    td[data-label="Status"] {
      display: inline-block;
      vertical-align: middle;
    }
    .wait {
      max-width: none;
    }
    .thesis {
      max-width: none;
      margin-top: 0.35rem;
    }
    .actions {
      flex-wrap: wrap;
    }
  }

  @keyframes rise {
    from {
      opacity: 0;
      transform: translateY(6px);
    }
    to {
      opacity: 1;
      transform: none;
    }
  }
  @keyframes pulse {
    50% {
      opacity: 0.35;
    }
  }
</style>
