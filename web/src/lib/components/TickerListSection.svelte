<script lang="ts">
  import type { ListKind, WatchlistTickerSummary } from "../types";
  import { emptySiblingCopy } from "../listVisibility";
  import TickerRow from "./TickerRow.svelte";

  interface Props {
    kind: ListKind;
    rows: WatchlistTickerSummary[];
    refreshing: Record<string, boolean>;
    selected: string | null;
    onselect: (ticker: string) => void;
    onrefresh: (ticker: string) => void;
    onremove: (ticker: string) => void;
    onprefillKind?: (kind: ListKind) => void;
  }

  let {
    kind,
    rows,
    refreshing,
    selected,
    onselect,
    onrefresh,
    onremove,
    onprefillKind,
  }: Props = $props();

  const title = $derived(kind === "held" ? "Held" : "Watched");
  const emptyCopy = $derived(emptySiblingCopy(kind));
</script>

<section class="list-block" data-kind={kind}>
  <h2>{title}</h2>
  {#if rows.length === 0}
    <p class="empty-sibling">
      {emptyCopy}
      {#if onprefillKind}
        <button
          type="button"
          class="cue"
          onclick={() => onprefillKind(kind)}
        >
          Use Add as {title}
        </button>
      {/if}
    </p>
  {:else}
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Ticker</th>
            <th>Status</th>
            <th>G / V / R</th>
            <th>Fwd P/E</th>
            <th>Conflicts</th>
            <th>Thesis</th>
            <th>Meta</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {#each rows as row, i (row.ticker)}
            <TickerRow
              {row}
              index={i}
              refreshing={!!refreshing[row.ticker]}
              selected={selected === row.ticker}
              {onselect}
              {onrefresh}
              {onremove}
            />
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</section>

<style>
  .list-block {
    margin-bottom: 2rem;
  }
  h2 {
    margin: 0 0 0.75rem;
    font-family: var(--font-display);
    font-size: 1.35rem;
    font-weight: 600;
  }
  .empty-sibling {
    color: var(--ink-soft);
    margin: 0;
    line-height: 1.45;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem 0.75rem;
  }
  .cue {
    border: 1px solid var(--line);
    background: transparent;
    color: var(--ink);
    padding: 0.45rem 0.7rem;
    min-height: 44px;
    border-radius: 2px;
    font-size: 0.85rem;
  }
  .table-wrap {
    overflow-x: auto;
    border-top: 1px solid var(--line);
  }
  table {
    width: 100%;
    border-collapse: collapse;
    min-width: 720px;
  }
  th {
    text-align: left;
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--ink-soft);
    font-weight: 500;
    padding: 0.5rem 0.65rem;
    border-bottom: 1px solid var(--line);
  }

  @media (max-width: 639px) {
    .table-wrap {
      overflow-x: visible;
    }
    table {
      min-width: 0;
      width: 100%;
      display: block;
    }
    thead {
      display: none;
    }
    table :global(tbody),
    table :global(tr),
    table :global(td) {
      display: block;
      width: 100%;
    }
    table :global(tr) {
      padding: 0.85rem 0;
      border-bottom: 1px solid var(--line);
    }
    table :global(td) {
      padding: 0.15rem 0;
      border: none;
    }
    table :global(td.ticker) {
      font-size: 1.15rem;
    }
    table :global(td.actions) {
      margin-top: 0.5rem;
    }
  }
</style>
