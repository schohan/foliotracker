<script lang="ts">
  import type { WatchlistCollection } from "../../types";

  interface Props {
    collections: WatchlistCollection[];
    activeId: string | null;
    busy?: boolean;
    onselect: (id: string | null) => void;
    oncreate: (name: string) => Promise<void> | void;
    onrename: (id: string, name: string) => Promise<void> | void;
    ondelete: (id: string) => Promise<void> | void;
  }

  let {
    collections,
    activeId,
    busy = false,
    onselect,
    oncreate,
    onrename,
    ondelete,
  }: Props = $props();

  let creating = $state(false);
  let renaming = $state(false);
  let draftName = $state("");

  const active = $derived(
    activeId ? collections.find((c) => c.id === activeId) ?? null : null,
  );

  function startCreate() {
    creating = true;
    renaming = false;
    draftName = "";
  }

  function startRename() {
    if (!active) return;
    renaming = true;
    creating = false;
    draftName = active.name;
  }

  function cancelEdit() {
    creating = false;
    renaming = false;
    draftName = "";
  }

  async function submitEdit() {
    const name = draftName.trim();
    if (!name || busy) return;
    if (creating) {
      await oncreate(name);
    } else if (renaming && active) {
      await onrename(active.id, name);
    }
    cancelEdit();
  }

  function onKey(e: KeyboardEvent) {
    if (e.key === "Enter") {
      e.preventDefault();
      void submitEdit();
    } else if (e.key === "Escape") {
      cancelEdit();
    }
  }
</script>

<div class="strip" role="region" aria-label="Watchlist collections">
  <div class="filters" role="toolbar" aria-label="Collection filters">
    <button
      type="button"
      class:active={activeId === null}
      aria-pressed={activeId === null}
      disabled={busy}
      onclick={() => onselect(null)}
    >
      All
    </button>
    {#each collections as c (c.id)}
      <button
        type="button"
        class:active={activeId === c.id}
        aria-pressed={activeId === c.id}
        disabled={busy}
        onclick={() => onselect(c.id)}
      >
        {c.name}
        <span class="count">{c.tickers.length}</span>
      </button>
    {/each}
  </div>

  <div class="manage">
    {#if creating || renaming}
      <input
        type="text"
        class="name-input"
        maxlength={40}
        placeholder={creating ? "Collection name" : "Rename collection"}
        bind:value={draftName}
        disabled={busy}
        onkeydown={onKey}
        aria-label={creating ? "New collection name" : "Rename collection"}
      />
      <button
        type="button"
        class="action"
        disabled={busy || !draftName.trim()}
        onclick={() => void submitEdit()}
      >
        Save
      </button>
      <button type="button" class="action ghost" disabled={busy} onclick={cancelEdit}>
        Cancel
      </button>
    {:else}
      <button type="button" class="action" disabled={busy} onclick={startCreate}>
        New collection…
      </button>
      {#if active}
        <button type="button" class="action ghost" disabled={busy} onclick={startRename}>
          Rename
        </button>
        <button
          type="button"
          class="action danger"
          disabled={busy}
          onclick={() => void ondelete(active.id)}
        >
          Delete
        </button>
      {/if}
    {/if}
  </div>
</div>

<style>
  .strip {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem 1rem;
    align-items: center;
    justify-content: space-between;
    margin: 0 0 1rem;
  }
  .filters {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
  }
  .filters button {
    border: 1px solid var(--line);
    background: white;
    color: var(--ink-soft);
    border-radius: 2px;
    padding: 0.35rem 0.65rem;
    min-height: 36px;
    font-size: 0.82rem;
  }
  .filters button.active {
    border-color: var(--ink);
    background: var(--ink);
    color: var(--paper);
  }
  .filters button:disabled {
    opacity: 0.5;
  }
  .count {
    margin-left: 0.25rem;
    opacity: 0.75;
    font-variant-numeric: tabular-nums;
  }
  .manage {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
    align-items: center;
  }
  .name-input {
    border: 1px solid var(--line);
    border-radius: 2px;
    padding: 0.4rem 0.55rem;
    min-height: 36px;
    min-width: 10rem;
    font: inherit;
    color: var(--ink);
    background: white;
  }
  .action {
    border: 1px solid var(--line);
    background: white;
    color: var(--ink);
    border-radius: 2px;
    padding: 0.35rem 0.65rem;
    min-height: 36px;
    font-size: 0.82rem;
  }
  .action.ghost {
    background: transparent;
  }
  .action.danger {
    border-color: var(--error);
    color: var(--error);
  }
  .action:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
</style>
