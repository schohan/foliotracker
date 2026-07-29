<script lang="ts">
  import type { ListKind } from "../types";

  interface Props {
    busy?: boolean;
    listKind?: ListKind;
    onadd: (ticker: string, listKind: ListKind) => void;
  }
  let {
    busy = false,
    listKind = $bindable("watched" as ListKind),
    onadd,
  }: Props = $props();

  let ticker = $state("");

  function submit(e: Event) {
    e.preventDefault();
    const t = ticker.trim().toUpperCase();
    if (!t || busy) return;
    onadd(t, listKind);
    ticker = "";
  }
</script>

<form class="add" onsubmit={submit}>
  <label class="sr">
    Ticker
    <input
      bind:value={ticker}
      placeholder="Add ticker"
      maxlength={12}
      disabled={busy}
      autocomplete="off"
      spellcheck="false"
    />
  </label>
  <select bind:value={listKind} disabled={busy} aria-label="List kind">
    <option value="watched">Watched</option>
    <option value="held">Held</option>
  </select>
  <button type="submit" disabled={busy || !ticker.trim()}>
    {busy ? "Adding…" : "Add"}
  </button>
</form>

<style>
  .add {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    align-items: center;
  }
  .sr {
    display: contents;
  }
  input,
  select,
  button {
    border: 1px solid var(--line);
    background: white;
    color: var(--ink);
    border-radius: 2px;
    padding: 0.55rem 0.75rem;
    min-height: 44px;
  }
  input {
    min-width: 9rem;
    letter-spacing: 0.04em;
  }
  button {
    background: var(--ink);
    color: var(--paper);
    border-color: var(--ink);
    font-weight: 500;
    min-width: 44px;
  }
  button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
</style>
