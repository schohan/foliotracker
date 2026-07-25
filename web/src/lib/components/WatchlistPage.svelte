<script lang="ts">
  import { onMount } from "svelte";
  import {
    addTicker,
    fetchResearch,
    fetchWatchlist,
    refreshAll,
    refreshTicker,
    removeTicker,
  } from "../api";
  import type {
    ListKind,
    Phase0Result,
    WatchlistState,
    WatchlistTickerSummary,
  } from "../types";
  import AddTickerForm from "./AddTickerForm.svelte";
  import DisclaimerBar from "./DisclaimerBar.svelte";
  import TickerDetailPanel from "./TickerDetailPanel.svelte";
  import TickerRow from "./TickerRow.svelte";

  let state = $state<WatchlistState | null>(null);
  let loadError = $state<string | null>(null);
  let busy = $state(false);
  let refreshing = $state<Record<string, boolean>>({});
  let selected = $state<string | null>(null);
  let detail = $state<Phase0Result | null>(null);
  let detailLoading = $state(false);
  let detailError = $state<string | null>(null);

  const held = $derived(
    (state?.summaries ?? []).filter((r) => r.list_kind === "held"),
  );
  const watched = $derived(
    (state?.summaries ?? []).filter((r) => r.list_kind === "watched"),
  );

  async function load() {
    loadError = null;
    try {
      state = await fetchWatchlist();
    } catch (e) {
      loadError = e instanceof Error ? e.message : String(e);
    }
  }

  onMount(() => {
    void load();
  });

  async function onAdd(ticker: string, listKind: ListKind) {
    busy = true;
    loadError = null;
    try {
      state = await addTicker(ticker, listKind);
      refreshing = { ...refreshing, [ticker]: true };
      await refreshTicker(ticker);
      state = await fetchWatchlist();
    } catch (e) {
      loadError = e instanceof Error ? e.message : String(e);
    } finally {
      refreshing = { ...refreshing, [ticker]: false };
      busy = false;
    }
  }

  async function onRefresh(ticker: string) {
    refreshing = { ...refreshing, [ticker]: true };
    loadError = null;
    try {
      await refreshTicker(ticker);
      state = await fetchWatchlist();
      if (selected === ticker) {
        await openDetail(ticker);
      }
    } catch (e) {
      loadError = e instanceof Error ? e.message : String(e);
    } finally {
      refreshing = { ...refreshing, [ticker]: false };
    }
  }

  async function onRefreshAll() {
    busy = true;
    loadError = null;
    try {
      await refreshAll();
      state = await fetchWatchlist();
    } catch (e) {
      loadError = e instanceof Error ? e.message : String(e);
    } finally {
      busy = false;
    }
  }

  async function onRemove(ticker: string) {
    loadError = null;
    try {
      state = await removeTicker(ticker);
      if (selected === ticker) {
        selected = null;
        detail = null;
      }
    } catch (e) {
      loadError = e instanceof Error ? e.message : String(e);
    }
  }

  async function openDetail(ticker: string) {
    selected = ticker;
    detailLoading = true;
    detailError = null;
    try {
      const res = await fetchResearch(ticker);
      detail = res.result;
    } catch (e) {
      detailError = e instanceof Error ? e.message : String(e);
      detail = null;
    } finally {
      detailLoading = false;
    }
  }

  function sectionRows(rows: WatchlistTickerSummary[]) {
    return rows;
  }
</script>

<div class="page">
  <header class="hero">
    <p class="brand">FolioTracker</p>
    <p class="tag">Held and watched names — evidence, scores, and thesis at a glance.</p>
  </header>

  <div class="toolbar">
    <AddTickerForm {busy} onadd={onAdd} />
    <button type="button" class="refresh-all" disabled={busy} onclick={onRefreshAll}>
      Refresh all
    </button>
  </div>

  {#if loadError}
    <p class="banner" role="alert">{loadError}</p>
  {/if}

  {#if !state}
    <p class="muted">Loading watchlist…</p>
  {:else}
    <section class="list-block">
      <h2>Held</h2>
      {#if held.length === 0}
        <p class="muted">No held tickers yet.</p>
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
              {#each sectionRows(held) as row, i (row.ticker)}
                <TickerRow
                  {row}
                  index={i}
                  refreshing={!!refreshing[row.ticker]}
                  selected={selected === row.ticker}
                  onselect={openDetail}
                  onrefresh={onRefresh}
                  onremove={onRemove}
                />
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </section>

    <section class="list-block">
      <h2>Watched</h2>
      {#if watched.length === 0}
        <p class="muted">No watched tickers yet.</p>
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
              {#each sectionRows(watched) as row, i (row.ticker)}
                <TickerRow
                  {row}
                  index={i}
                  refreshing={!!refreshing[row.ticker]}
                  selected={selected === row.ticker}
                  onselect={openDetail}
                  onrefresh={onRefresh}
                  onremove={onRemove}
                />
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </section>
  {/if}

  <DisclaimerBar text={state?.disclaimer ?? "FolioTracker output is for informational and educational purposes only. It is not investment, legal, or tax advice. Do your own research."} />
</div>

{#if selected}
  <TickerDetailPanel
    result={detail}
    loading={detailLoading}
    error={detailError}
    onclose={() => {
      selected = null;
      detail = null;
      detailError = null;
    }}
  />
{/if}

<style>
  .page {
    max-width: 1100px;
    margin: 0 auto;
    padding: 2.5rem 1.25rem 0;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
  }
  .hero {
    margin-bottom: 1.75rem;
  }
  .brand {
    margin: 0;
    font-family: var(--font-display);
    font-size: clamp(2.6rem, 6vw, 3.8rem);
    font-weight: 700;
    letter-spacing: -0.02em;
    line-height: 1;
    color: var(--ink);
  }
  .tag {
    margin: 0.65rem 0 0;
    max-width: 32rem;
    color: var(--ink-soft);
    font-size: 1.05rem;
    line-height: 1.4;
  }
  .toolbar {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 1.25rem;
  }
  .refresh-all {
    border: 1px solid var(--ink);
    background: transparent;
    color: var(--ink);
    padding: 0.55rem 0.9rem;
    border-radius: 2px;
    font-weight: 500;
  }
  .refresh-all:disabled {
    opacity: 0.5;
  }
  .list-block {
    margin-bottom: 2rem;
  }
  h2 {
    margin: 0 0 0.75rem;
    font-family: var(--font-display);
    font-size: 1.35rem;
    font-weight: 600;
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
  .muted {
    color: var(--ink-soft);
  }
  .banner {
    background: rgba(163, 32, 32, 0.08);
    color: var(--error);
    padding: 0.65rem 0.85rem;
    margin: 0 0 1rem;
  }
  :global(.page > :last-child) {
    margin-top: auto;
  }
</style>
