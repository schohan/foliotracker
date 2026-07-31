<script lang="ts">
  import { onMount } from "svelte";
  import { fetchRisk } from "../api";
  import {
    formatCorrelation,
    formatRiskScore,
    formatWeightPercent,
  } from "../riskFormat";
  import type { AppView, PortfolioRiskSnapshot } from "../types";
  import DisclaimerBar from "./DisclaimerBar.svelte";
  import PrimaryNav from "./PrimaryNav.svelte";

  interface Props {
    view: AppView;
    onnavigate: (view: AppView) => void;
  }

  let { view, onnavigate }: Props = $props();

  let snap = $state<PortfolioRiskSnapshot | null>(null);
  let loadError = $state<string | null>(null);
  let loading = $state(true);

  const emptyHeld = $derived(snap != null && snap.held_count === 0);
  const corrPairs = $derived(snap?.top_correlations ?? []);
  const showCorrEmpty = $derived(
    snap != null && snap.held_count >= 2 && corrPairs.length === 0,
  );

  async function load() {
    loading = true;
    loadError = null;
    try {
      snap = await fetchRisk();
    } catch (e) {
      loadError = e instanceof Error ? e.message : String(e);
    } finally {
      loading = false;
    }
  }

  onMount(() => {
    void load();
  });

  const defaultDisclaimer =
    "FolioTracker output is for informational and educational purposes only. It is not investment, legal, or tax advice. Do your own research.";
</script>

<main class="page">
  <header class="hero">
    <p class="brand">FolioTracker</p>
    <PrimaryNav {view} {onnavigate} />
    <p class="tag">
      Held concentration and co-movement — equal-weight sector mix, risk scores,
      and top pairwise correlations (~1y). Not advice.
    </p>
  </header>

  {#if loadError}
    <div class="banner" role="alert">
      <p>{loadError}</p>
      <button type="button" class="retry" onclick={() => void load()}>
        Retry
      </button>
    </div>
  {/if}

  {#if loading && !snap}
    <p class="muted">Loading risk…</p>
  {:else if emptyHeld}
    <p class="empty">
      Nothing held yet. Add a ticker as Held on Watchlist to see concentration
      and co-movement.
    </p>
    <button
      type="button"
      class="goto"
      onclick={() => onnavigate("watchlist")}
    >
      Go to Watchlist
    </button>
  {:else if snap}
    <div class="meta" aria-live="polite">
      <p>
        <span class="status status-{snap.status}">{snap.status}</span>
        · {snap.held_count} held
        · equal-weight
        · top name {formatWeightPercent(snap.top_name_weight)}
        · avg risk {formatRiskScore(snap.avg_risk_score)}
        {#if snap.risk_scores_known < snap.held_count}
          <span class="muted">
            ({snap.risk_scores_known}/{snap.held_count} scores)
          </span>
        {/if}
        {#if snap.held_count >= 2}
          · {snap.correlation_pairs_known} corr pairs
        {/if}
      </p>
    </div>

    {#if snap.gaps.length > 0}
      <ul class="gaps">
        {#each snap.gaps as gap (gap)}
          <li>{gap}</li>
        {/each}
      </ul>
    {/if}

    <section class="block" aria-labelledby="sector-heading">
      <h2 id="sector-heading">Sector concentration</h2>
      <table>
        <thead>
          <tr>
            <th scope="col">Sector</th>
            <th scope="col">Weight</th>
            <th scope="col">Names</th>
          </tr>
        </thead>
        <tbody>
          {#each snap.sector_buckets as bucket (bucket.sector)}
            <tr>
              <td class="sector">{bucket.sector}</td>
              <td>{formatWeightPercent(bucket.weight)}</td>
              <td class="names">{bucket.tickers.join(", ")}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </section>

    <section class="block" aria-labelledby="names-heading">
      <h2 id="names-heading">Held names</h2>
      <table>
        <thead>
          <tr>
            <th scope="col">Ticker</th>
            <th scope="col">Weight</th>
            <th scope="col">Sector</th>
            <th scope="col">Risk</th>
          </tr>
        </thead>
        <tbody>
          {#each snap.positions as pos (pos.ticker)}
            <tr>
              <td class="ticker">{pos.ticker}</td>
              <td>{formatWeightPercent(pos.weight)}</td>
              <td>{pos.sector ?? "—"}</td>
              <td>{formatRiskScore(pos.risk_score)}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </section>

    {#if snap.held_count >= 2}
      <section class="block" aria-labelledby="corr-heading">
        <h2 id="corr-heading">Top correlations</h2>
        {#if showCorrEmpty}
          <p class="empty">
            No pairwise correlations yet. Refresh Held research so Yahoo price
            history lands in the source cache (need overlapping ~1y daily
            returns).
          </p>
        {:else}
          <table>
            <thead>
              <tr>
                <th scope="col">Pair</th>
                <th scope="col">Corr</th>
                <th scope="col">Overlap</th>
                <th scope="col">Window</th>
              </tr>
            </thead>
            <tbody>
              {#each corrPairs as pair (`${pair.ticker_a}-${pair.ticker_b}`)}
                <tr>
                  <td class="ticker">{pair.ticker_a} · {pair.ticker_b}</td>
                  <td>{formatCorrelation(pair.correlation)}</td>
                  <td class="muted">{pair.overlap_days}d</td>
                  <td class="names">{pair.window}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        {/if}
      </section>
    {/if}
  {/if}

  <DisclaimerBar text={snap?.disclaimer ?? defaultDisclaimer} />
</main>

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
    max-width: 36rem;
    color: var(--ink-soft);
    font-size: 1.05rem;
    line-height: 1.4;
  }
  .muted {
    color: var(--ink-soft);
  }
  .empty {
    margin: 0 0 1rem;
    color: var(--ink-soft);
    max-width: 28rem;
    line-height: 1.45;
  }
  .goto {
    align-self: flex-start;
    border: 1px solid var(--ink);
    background: var(--ink);
    color: var(--paper);
    padding: 0.55rem 0.9rem;
    min-height: 44px;
    border-radius: 2px;
    font-weight: 500;
    margin-bottom: 1.5rem;
  }
  .meta p {
    margin: 0 0 1rem;
    color: var(--ink-soft);
    font-size: 0.95rem;
  }
  .status {
    font-weight: 600;
    text-transform: lowercase;
  }
  .status-ok {
    color: var(--ok);
  }
  .status-partial {
    color: var(--partial);
  }
  .status-error {
    color: var(--error);
  }
  .gaps {
    margin: 0 0 1.25rem;
    padding-left: 1.1rem;
    color: var(--partial);
    font-size: 0.9rem;
    line-height: 1.45;
  }
  .block {
    margin-bottom: 1.75rem;
  }
  .block h2 {
    margin: 0 0 0.65rem;
    font-family: var(--font-display);
    font-size: 1.35rem;
    font-weight: 600;
  }
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
  .ticker,
  .sector {
    font-family: var(--font-display);
    font-weight: 600;
  }
  .names {
    color: var(--ink-soft);
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
  :global(.page > :last-child) {
    margin-top: auto;
  }
</style>
