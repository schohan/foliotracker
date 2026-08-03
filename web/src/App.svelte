<script lang="ts">
  import BriefPage from "./lib/components/BriefPage.svelte";
  import RiskPage from "./lib/components/RiskPage.svelte";
  import WatchlistPage from "./lib/components/WatchlistPage.svelte";
  import type { AppView } from "./lib/types";

  let view = $state<AppView>("watchlist");

  function onnavigate(next: AppView) {
    view = next;
  }
</script>

{#if view === "watchlist"}
  <WatchlistPage {view} {onnavigate} />
{:else if view === "risk"}
  <RiskPage {view} {onnavigate} />
{:else}
  <BriefPage {view} {onnavigate} />
{/if}
