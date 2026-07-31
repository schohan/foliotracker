<script lang="ts">
  import type { AppView } from "../types";

  interface Props {
    view: AppView;
    onnavigate: (view: AppView) => void;
  }

  let { view, onnavigate }: Props = $props();
</script>

<nav class="nav" aria-label="Primary">
  <button
    type="button"
    class="link"
    class:active={view === "watchlist"}
    aria-current={view === "watchlist" ? "page" : undefined}
    onclick={() => onnavigate("watchlist")}
  >
    Watchlist
  </button>
  <span class="sep" aria-hidden="true">|</span>
  <button
    type="button"
    class="link"
    class:active={view === "risk"}
    aria-current={view === "risk" ? "page" : undefined}
    onclick={() => onnavigate("risk")}
  >
    Risk
  </button>
</nav>

<style>
  .nav {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.55rem;
    margin: 1rem 0 0;
    font-size: 1rem;
  }
  .sep {
    color: var(--line);
    user-select: none;
  }
  .link {
    border: none;
    background: transparent;
    color: var(--ink-soft);
    padding: 0.35rem 0.15rem;
    min-height: 44px;
    border-radius: 2px;
    font-weight: 500;
  }
  .link.active {
    color: var(--ink);
    font-weight: 600;
    box-shadow: inset 0 -2px 0 var(--accent);
  }
</style>
