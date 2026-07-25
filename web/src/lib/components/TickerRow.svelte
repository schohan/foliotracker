<script lang="ts">
  import type { WatchlistTickerSummary } from "../types";
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
</script>

<tr
  class:selected
  class:refreshing
  style={`--i: ${index}`}
  onclick={() => onselect(row.ticker)}
  onkeydown={(e) => e.key === "Enter" && onselect(row.ticker)}
  tabindex="0"
>
  <td class="ticker">{row.ticker}</td>
  <td>
    <span class={`status ${row.status ?? "none"}`}>{row.status ?? "—"}</span>
  </td>
  <td>
    <ScoreStrip
      growth={row.growth_score}
      value={row.value_score}
      risk={row.risk_score}
    />
  </td>
  <td class="num">{row.forward_pe == null ? "—" : row.forward_pe.toFixed(1)}</td>
  <td class="num">{row.conflict_count}</td>
  <td class="thesis">{row.thesis_one_liner ?? row.error_message ?? "—"}</td>
  <td class="meta">
    {#if row.cache_hit}
      <span title="Served from cache">cache</span>
    {/if}
    {#if row.request_id}
      <code title={row.request_id}>{row.request_id.slice(0, 8)}</code>
    {/if}
  </td>
  <td class="actions" onclick={(e) => e.stopPropagation()}>
    <button type="button" disabled={refreshing} onclick={() => onrefresh(row.ticker)}>
      {refreshing ? "…" : "Refresh"}
    </button>
    <button type="button" class="ghost" onclick={() => onremove(row.ticker)}>Remove</button>
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
  .actions button {
    border: 1px solid var(--line);
    background: white;
    padding: 0.35rem 0.55rem;
    border-radius: 2px;
    font-size: 0.8rem;
  }
  .actions .ghost {
    background: transparent;
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
