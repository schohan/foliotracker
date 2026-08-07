<script lang="ts">
  import { onMount, tick } from "svelte";
  import {
    addTicker,
    bulkWatchlistTickers,
    collectionMembers,
    createCollection,
    deleteCollection,
    fetchResearch,
    fetchWatchlist,
    intakeTickers,
    refreshAll,
    refreshTicker,
    removeTicker,
    renameCollection,
  } from "../api";
  import { rowFocusId } from "../focusHelpers";
  import {
    listVisibility,
    showListSections,
  } from "../listVisibility";
  import type {
    AppView,
    BulkAction,
    ListKind,
    Phase0Result,
    WatchlistCollection,
    WatchlistIntakeResponse,
    WatchlistState,
    WatchlistTickerSummary,
  } from "../types";
  import AddTickerForm from "./AddTickerForm.svelte";
  import DisclaimerBar from "./DisclaimerBar.svelte";
  import PrimaryNav from "./PrimaryNav.svelte";
  import TickerDetailPanel from "./TickerDetailPanel.svelte";
  import TickerIntakePanel from "./TickerIntakePanel.svelte";
  import TickerListSection from "./TickerListSection.svelte";
  import CollectionsBar from "./watchlist/CollectionsBar.svelte";

  interface Props {
    view: AppView;
    onnavigate: (view: AppView) => void;
  }

  let { view, onnavigate }: Props = $props();

  let state = $state<WatchlistState | null>(null);
  let loadError = $state<string | null>(null);
  let adding = $state(false);
  let intakeBusy = $state(false);
  let refreshAllBusy = $state(false);
  let refreshing = $state<Record<string, boolean>>({});
  let selected = $state<string | null>(null);
  let detail = $state<Phase0Result | null>(null);
  let detailLoading = $state(false);
  let detailError = $state<string | null>(null);
  let formListKind = $state<ListKind>("watched");
  let checkedTickers: string[] = $state([]);
  let bulkBusy = $state(false);
  let bulkStatus: string | null = $state(null);
  let activeCollectionId: string | null = $state(null);
  let collectionBusy = $state(false);
  let addToCollectionId = $state("");

  const collections = $derived(state?.collections ?? []);
  const activeCollection = $derived(
    activeCollectionId
      ? (collections.find((c) => c.id === activeCollectionId) ?? null)
      : null,
  );
  const collectionFilter = $derived(
    activeCollection ? new Set(activeCollection.tickers) : null,
  );

  const heldAll = $derived(
    (state?.summaries ?? []).filter((r) => r.list_kind === "held"),
  );
  const watchedAll = $derived(
    (state?.summaries ?? []).filter((r) => r.list_kind === "watched"),
  );
  const held = $derived(
    collectionFilter
      ? heldAll.filter((r) => collectionFilter.has(r.ticker))
      : heldAll,
  );
  const watched = $derived(
    collectionFilter
      ? watchedAll.filter((r) => collectionFilter.has(r.ticker))
      : watchedAll,
  );
  const visibility = $derived(listVisibility(heldAll.length, watchedAll.length));
  const firstRun = $derived(visibility === "first-run");
  const showSections = $derived(showListSections(visibility));
  const tagline = $derived(
    firstRun
      ? "Add a ticker to start grounded research."
      : "Held and watched names — evidence, scores, and thesis at a glance.",
  );
  const selectedRefreshing = $derived(
    selected ? !!refreshing[selected] : false,
  );
  const checkedCount = $derived(checkedTickers.length);
  const checkedSet: Set<string> = $derived(new Set(checkedTickers));
  const pageBusy = $derived(
    adding || intakeBusy || refreshAllBusy || bulkBusy || collectionBusy,
  );
  const filterEmpty = $derived(
    !!collectionFilter && held.length === 0 && watched.length === 0,
  );

  async function load() {
    loadError = null;
    try {
      state = await fetchWatchlist();
      syncActiveCollection(state.collections);
    } catch (e) {
      loadError = e instanceof Error ? e.message : String(e);
    }
  }

  function syncActiveCollection(cols: WatchlistCollection[]) {
    if (activeCollectionId && !cols.some((c) => c.id === activeCollectionId)) {
      activeCollectionId = null;
    }
    if (
      addToCollectionId &&
      !cols.some((c) => c.id === addToCollectionId)
    ) {
      addToCollectionId = cols[0]?.id ?? "";
    } else if (!addToCollectionId && cols.length > 0) {
      addToCollectionId = cols[0].id;
    }
  }

  onMount(() => {
    void load();
  });

  function setRefreshing(ticker: string, value: boolean) {
    refreshing = { ...refreshing, [ticker]: value };
  }

  function setRefreshingMany(tickers: string[], value: boolean) {
    const next = { ...refreshing };
    for (const t of tickers) next[t] = value;
    refreshing = next;
  }

  /** Bulk intake: membership only — no auto research (refresh remains explicit). */
  async function onIntake(
    text: string,
    listKind: ListKind,
  ): Promise<WatchlistIntakeResponse> {
    intakeBusy = true;
    loadError = null;
    try {
      const res = await intakeTickers(text, listKind);
      state = res.state;
      syncActiveCollection(res.state.collections);
      return res;
    } catch (e) {
      loadError = e instanceof Error ? e.message : String(e);
      throw e;
    } finally {
      intakeBusy = false;
    }
  }

  /** Membership-first: form unlocks after POST; research continues in background. */
  async function onAdd(ticker: string, listKind: ListKind) {
    adding = true;
    loadError = null;
    try {
      state = await addTicker(ticker, listKind);
      syncActiveCollection(state.collections);
    } catch (e) {
      loadError = e instanceof Error ? e.message : String(e);
      adding = false;
      return;
    }
    adding = false;
    setRefreshing(ticker, true);
    try {
      await refreshTicker(ticker);
      state = await fetchWatchlist();
      syncActiveCollection(state.collections);
    } catch (e) {
      loadError = e instanceof Error ? e.message : String(e);
    } finally {
      setRefreshing(ticker, false);
      if (selected === ticker) {
        await loadDetailIfIdle(ticker);
      }
    }
  }

  async function onRefresh(ticker: string) {
    setRefreshing(ticker, true);
    loadError = null;
    try {
      await refreshTicker(ticker);
      state = await fetchWatchlist();
      syncActiveCollection(state.collections);
    } catch (e) {
      loadError = e instanceof Error ? e.message : String(e);
    } finally {
      setRefreshing(ticker, false);
      if (selected === ticker) {
        await loadDetailIfIdle(ticker);
      }
    }
  }

  async function onRefreshAll() {
    const tickers = (state?.summaries ?? []).map((s) => s.ticker);
    if (tickers.length === 0) return;
    refreshAllBusy = true;
    loadError = null;
    setRefreshingMany(tickers, true);
    try {
      await refreshAll();
      state = await fetchWatchlist();
      syncActiveCollection(state.collections);
    } catch (e) {
      loadError = e instanceof Error ? e.message : String(e);
    } finally {
      setRefreshingMany(tickers, false);
      refreshAllBusy = false;
      if (selected && !refreshing[selected]) {
        await loadDetailIfIdle(selected);
      }
    }
  }

  async function onRemove(ticker: string) {
    loadError = null;
    try {
      state = await removeTicker(ticker);
      syncActiveCollection(state.collections);
      checkedTickers = checkedTickers.filter((t) => t !== ticker);
      if (selected === ticker) {
        selected = null;
        detail = null;
        detailError = null;
      }
    } catch (e) {
      loadError = e instanceof Error ? e.message : String(e);
    }
  }

  function toggleChecked(ticker: string, checked: boolean) {
    if (checked) {
      if (!checkedTickers.includes(ticker)) {
        checkedTickers = [...checkedTickers, ticker];
      }
    } else {
      checkedTickers = checkedTickers.filter((t) => t !== ticker);
    }
  }

  function toggleSection(kind: ListKind, checked: boolean) {
    const rows: WatchlistTickerSummary[] = kind === "held" ? held : watched;
    const sectionTickers = rows.map((r) => r.ticker);
    if (checked) {
      const next = new Set(checkedTickers);
      for (const t of sectionTickers) next.add(t);
      checkedTickers = Array.from(next);
    } else {
      const drop = new Set(sectionTickers);
      checkedTickers = checkedTickers.filter((t) => !drop.has(t));
    }
  }

  function clearChecked() {
    checkedTickers = [];
    bulkStatus = null;
  }

  async function onBulk(action: BulkAction) {
    const tickers = [...checkedTickers];
    if (tickers.length === 0 || bulkBusy) return;
    bulkBusy = true;
    loadError = null;
    bulkStatus = null;
    try {
      const res = await bulkWatchlistTickers(tickers, action);
      state = res.state;
      syncActiveCollection(res.state.collections);
      const parts = [
        `${res.affected_count} ${action === "remove" ? "removed" : "moved"}`,
      ];
      if (res.skipped_noop_count) {
        parts.push(`${res.skipped_noop_count} already there`);
      }
      if (res.skipped_not_found_count) {
        parts.push(`${res.skipped_not_found_count} not found`);
      }
      bulkStatus = parts.join(" · ");
      const affected = new Set(res.affected);
      const membership = new Set([
        ...res.state.membership.held,
        ...res.state.membership.watched,
      ]);
      checkedTickers = checkedTickers.filter(
        (t) => !affected.has(t) && membership.has(t),
      );
      if (selected && !membership.has(selected)) {
        selected = null;
        detail = null;
        detailError = null;
      }
    } catch (e) {
      loadError = e instanceof Error ? e.message : String(e);
    } finally {
      bulkBusy = false;
    }
  }

  async function onCreateCollection(name: string) {
    collectionBusy = true;
    loadError = null;
    try {
      state = await createCollection(name);
      const created = state.collections.find(
        (c) => c.name.toLowerCase() === name.trim().toLowerCase(),
      );
      if (created) {
        activeCollectionId = created.id;
        addToCollectionId = created.id;
      }
      syncActiveCollection(state.collections);
    } catch (e) {
      loadError = e instanceof Error ? e.message : String(e);
    } finally {
      collectionBusy = false;
    }
  }

  async function onRenameCollection(id: string, name: string) {
    collectionBusy = true;
    loadError = null;
    try {
      await renameCollection(id, name);
      state = await fetchWatchlist();
      syncActiveCollection(state.collections);
    } catch (e) {
      loadError = e instanceof Error ? e.message : String(e);
    } finally {
      collectionBusy = false;
    }
  }

  async function onDeleteCollection(id: string) {
    collectionBusy = true;
    loadError = null;
    try {
      state = await deleteCollection(id);
      if (activeCollectionId === id) activeCollectionId = null;
      syncActiveCollection(state.collections);
    } catch (e) {
      loadError = e instanceof Error ? e.message : String(e);
    } finally {
      collectionBusy = false;
    }
  }

  async function onAddToCollection() {
    const tickers = [...checkedTickers];
    const id = addToCollectionId;
    if (!id || tickers.length === 0 || bulkBusy) return;
    bulkBusy = true;
    loadError = null;
    bulkStatus = null;
    try {
      const res = await collectionMembers(id, tickers, "add");
      state = res.state;
      syncActiveCollection(res.state.collections);
      const name =
        res.collection.name ||
        collections.find((c) => c.id === id)?.name ||
        "collection";
      const parts = [`${res.affected_count} added to ${name}`];
      if (res.skipped_noop_count) {
        parts.push(`${res.skipped_noop_count} already in`);
      }
      if (res.skipped_not_found_count) {
        parts.push(`${res.skipped_not_found_count} not on watchlist`);
      }
      bulkStatus = parts.join(" · ");
    } catch (e) {
      loadError = e instanceof Error ? e.message : String(e);
    } finally {
      bulkBusy = false;
    }
  }

  async function onRemoveFromCollection() {
    const tickers = [...checkedTickers];
    const col = activeCollection;
    if (!col || tickers.length === 0 || bulkBusy) return;
    bulkBusy = true;
    loadError = null;
    bulkStatus = null;
    try {
      const res = await collectionMembers(col.id, tickers, "remove");
      state = res.state;
      syncActiveCollection(res.state.collections);
      const parts = [`${res.affected_count} removed from ${col.name}`];
      if (res.skipped_not_found_count) {
        parts.push(`${res.skipped_not_found_count} not in collection`);
      }
      bulkStatus = parts.join(" · ");
      const drop = new Set(res.affected);
      checkedTickers = checkedTickers.filter((t) => !drop.has(t));
    } catch (e) {
      loadError = e instanceof Error ? e.message : String(e);
    } finally {
      bulkBusy = false;
    }
  }

  /** UI single-flight: never fetchResearch while that ticker is refreshing. */
  async function loadDetailIfIdle(ticker: string) {
    if (refreshing[ticker]) {
      detailLoading = false;
      return;
    }
    detailLoading = true;
    detailError = null;
    try {
      const res = await fetchResearch(ticker);
      if (selected === ticker && !refreshing[ticker]) {
        detail = res.result;
      }
    } catch (e) {
      if (selected === ticker) {
        detailError = e instanceof Error ? e.message : String(e);
        detail = null;
      }
    } finally {
      detailLoading = false;
    }
  }

  async function openDetail(ticker: string) {
    selected = ticker;
    detailError = null;
    if (refreshing[ticker]) {
      detailLoading = false;
      return;
    }
    await loadDetailIfIdle(ticker);
  }

  async function closeDetail() {
    const was = selected;
    selected = null;
    detail = null;
    detailError = null;
    detailLoading = false;
    await tick();
    if (was) {
      document.getElementById(rowFocusId(was))?.focus();
    }
  }

  function prefillKind(kind: ListKind) {
    formListKind = kind;
  }

  const defaultDisclaimer =
    "FolioTracker output is for informational and educational purposes only. It is not investment, legal, or tax advice. Do your own research.";
</script>

<main class="page">
  <header class="hero">
    <p class="brand">FolioTracker</p>
    <PrimaryNav {view} {onnavigate} />
    <p class="tag">{tagline}</p>
  </header>

  <div class="toolbar">
    <AddTickerForm
      busy={pageBusy}
      bind:listKind={formListKind}
      onadd={onAdd}
    />
    {#if !firstRun}
      <button
        type="button"
        class="refresh-all"
        disabled={pageBusy}
        onclick={onRefreshAll}
      >
        {refreshAllBusy ? "Refreshing…" : "Refresh all"}
      </button>
    {/if}
  </div>

  <TickerIntakePanel
    busy={pageBusy}
    bind:listKind={formListKind}
    onintake={onIntake}
  />

  {#if !firstRun}
    <CollectionsBar
      {collections}
      activeId={activeCollectionId}
      busy={pageBusy}
      onselect={(id) => {
        activeCollectionId = id;
      }}
      oncreate={onCreateCollection}
      onrename={onRenameCollection}
      ondelete={onDeleteCollection}
    />
  {/if}

  {#if checkedCount > 0}
    <div class="bulk-bar" role="region" aria-label="Bulk ticker actions">
      <span class="bulk-count">{checkedCount} selected</span>
      <button
        type="button"
        class="bulk-btn"
        disabled={bulkBusy}
        onclick={() => void onBulk("move_to_held")}
      >
        Move to Held
      </button>
      <button
        type="button"
        class="bulk-btn"
        disabled={bulkBusy}
        onclick={() => void onBulk("move_to_watched")}
      >
        Move to Watched
      </button>
      {#if collections.length > 0}
        <label class="add-to">
          <span class="sr-only">Add to collection</span>
          <select
            bind:value={addToCollectionId}
            disabled={bulkBusy}
            aria-label="Collection to add to"
          >
            {#each collections as c (c.id)}
              <option value={c.id}>{c.name}</option>
            {/each}
          </select>
          <button
            type="button"
            class="bulk-btn"
            disabled={bulkBusy || !addToCollectionId}
            onclick={() => void onAddToCollection()}
          >
            Add to collection
          </button>
        </label>
      {/if}
      {#if activeCollection}
        <button
          type="button"
          class="bulk-btn"
          disabled={bulkBusy}
          onclick={() => void onRemoveFromCollection()}
        >
          Remove from {activeCollection.name}
        </button>
      {/if}
      <button
        type="button"
        class="bulk-btn danger"
        disabled={bulkBusy}
        onclick={() => void onBulk("remove")}
      >
        {bulkBusy ? "Working…" : "Remove"}
      </button>
      <button
        type="button"
        class="bulk-btn ghost"
        disabled={bulkBusy}
        onclick={clearChecked}
      >
        Clear
      </button>
    </div>
  {/if}
  {#if bulkStatus}
    <p class="bulk-status" aria-live="polite">{bulkStatus}</p>
  {/if}

  {#if loadError}
    <div class="banner" role="alert">
      <p>{loadError}</p>
      <button type="button" class="retry" onclick={() => void load()}>
        Retry
      </button>
    </div>
  {/if}

  {#if !state}
    <p class="muted">Loading watchlist…</p>
  {:else if showSections}
    {#if filterEmpty}
      <p class="muted filter-empty">
        No tickers in {activeCollection?.name ?? "this collection"} yet. Select
        rows and use Add to collection.
      </p>
    {/if}
    <TickerListSection
      kind="held"
      rows={held}
      {refreshing}
      {selected}
      checkedTickers={checkedSet}
      onselect={openDetail}
      ontoggle={toggleChecked}
      ontoggleSection={toggleSection}
      onrefresh={onRefresh}
      onremove={onRemove}
      onprefillKind={prefillKind}
    />
    <TickerListSection
      kind="watched"
      rows={watched}
      {refreshing}
      {selected}
      checkedTickers={checkedSet}
      onselect={openDetail}
      ontoggle={toggleChecked}
      ontoggleSection={toggleSection}
      onrefresh={onRefresh}
      onremove={onRemove}
      onprefillKind={prefillKind}
    />
  {/if}

  <DisclaimerBar text={state?.disclaimer ?? defaultDisclaimer} />
</main>

{#if selected}
  <TickerDetailPanel
    result={detail}
    loading={detailLoading}
    error={detailError}
    refreshing={selectedRefreshing}
    ticker={selected}
    onclose={closeDetail}
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
    min-height: 44px;
    border-radius: 2px;
    font-weight: 500;
  }
  .refresh-all:disabled {
    opacity: 0.5;
  }
  .muted {
    color: var(--ink-soft);
  }
  .filter-empty {
    margin: 0 0 0.85rem;
    font-size: 0.95rem;
  }
  .banner {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.75rem;
    background: rgba(163, 32, 32, 0.08);
    color: var(--error);
    padding: 0.65rem 0.85rem;
    margin: 0 0 1rem;
  }
  .banner p {
    margin: 0;
    flex: 1 1 12rem;
  }
  .retry {
    border: 1px solid var(--error);
    background: transparent;
    color: var(--error);
    padding: 0.45rem 0.75rem;
    min-height: 44px;
    min-width: 44px;
    border-radius: 2px;
    font-weight: 500;
  }
  .bulk-bar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem;
    margin: 0 0 0.75rem;
    padding: 0.65rem 0;
    border-top: 1px solid var(--line);
    border-bottom: 1px solid var(--line);
    position: sticky;
    top: 0;
    z-index: 2;
    background: var(--paper);
  }
  .bulk-count {
    font-weight: 600;
    color: var(--ink);
    margin-right: 0.35rem;
    min-width: 5.5rem;
  }
  .bulk-btn {
    border: 1px solid var(--line);
    background: white;
    color: var(--ink);
    border-radius: 2px;
    padding: 0.5rem 0.75rem;
    min-height: 44px;
    font-size: 0.9rem;
  }
  .bulk-btn.danger {
    border-color: var(--error);
    color: var(--error);
  }
  .bulk-btn.ghost {
    background: transparent;
  }
  .bulk-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  .add-to {
    display: inline-flex;
    flex-wrap: wrap;
    gap: 0.35rem;
    align-items: center;
  }
  .add-to select {
    border: 1px solid var(--line);
    border-radius: 2px;
    padding: 0.45rem 0.55rem;
    min-height: 44px;
    background: white;
    color: var(--ink);
    font: inherit;
  }
  .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
  }
  .bulk-status {
    margin: 0 0 0.85rem;
    color: var(--ink-soft);
    font-size: 0.9rem;
  }
  :global(.page > :last-child) {
    margin-top: auto;
  }
</style>
