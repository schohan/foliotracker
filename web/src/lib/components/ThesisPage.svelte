<script lang="ts">
  import { onMount } from "svelte";
  import { fetchThesis, generateThesis } from "../api";
  import type { AppView, ThesisDashboard } from "../types";
  import DisclaimerBar from "./DisclaimerBar.svelte";
  import PrimaryNav from "./PrimaryNav.svelte";
  import AssetBreakdown from "./thesis/AssetBreakdown.svelte";
  import FrameworkScorecard from "./thesis/FrameworkScorecard.svelte";
  import FrameworkScoreTable from "./thesis/FrameworkScoreTable.svelte";
  import MarginOfSafety from "./thesis/MarginOfSafety.svelte";
  import ValuationLadder from "./thesis/ValuationLadder.svelte";
  import { formatValuationValue } from "../thesisFormat";

  interface Props {
    view: AppView;
    onnavigate: (view: AppView) => void;
  }

  let { view, onnavigate }: Props = $props();

  let dashboard = $state<ThesisDashboard | null>(null);
  let loadError = $state<string | null>(null);
  let loading = $state(true);
  let generating = $state(false);
  let selectedTicker = $state<string | null>(null);

  const emptyUniverse = $derived(
    dashboard != null && dashboard.universe_count === 0,
  );
  const selectedRow = $derived(
    dashboard?.tickers.find((t) => t.ticker === selectedTicker) ?? null,
  );

  async function load() {
    loading = true;
    loadError = null;
    try {
      dashboard = await fetchThesis();
    } catch (e) {
      loadError = e instanceof Error ? e.message : String(e);
    } finally {
      loading = false;
    }
  }

  async function generate() {
    if (generating) return;
    generating = true;
    loadError = null;
    try {
      dashboard = await generateThesis();
      if (
        selectedTicker != null &&
        !dashboard.tickers.some((t) => t.ticker === selectedTicker)
      ) {
        selectedTicker = null;
      }
    } catch (e) {
      loadError = e instanceof Error ? e.message : String(e);
    } finally {
      generating = false;
    }
  }

  function onselect(ticker: string) {
    selectedTicker = selectedTicker === ticker ? null : ticker;
  }

  onMount(() => {
    void load();
  });

  const defaultDisclaimer =
    "FolioTracker output is for informational and educational purposes only. It is not investment, legal, or tax advice. Do your own research.";

  function formatGeneratedAt(iso: string): string {
    const d = new Date(iso);
    return Number.isNaN(d.getTime()) ? iso : d.toLocaleString();
  }
</script>

<main class="page">
  <header class="hero">
    <p class="brand">FolioTracker</p>
    <PrimaryNav {view} {onnavigate} />
    <p class="tag">
      Every holding through multiple investment lenses — deterministic Graham
      Deep Value and Financial Strength scorecards, multi-method valuations,
      and net-asset intelligence from merged fundamentals. Gaps stay honest. Not
      advice.
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

  <div class="actions">
    <button
      type="button"
      class="generate"
      disabled={generating}
      onclick={() => void generate()}
    >
      {generating ? "Generating…" : "Generate"}
    </button>
    {#if dashboard}
      <p class="meta" aria-live="polite">
        <span class="status status-{dashboard.generation_status}">
          {dashboard.generation_status}
        </span>
        · {formatGeneratedAt(dashboard.generated_at)}
        · {dashboard.tickers_considered}/{dashboard.universe_count} tickers
      </p>
    {/if}
  </div>

  {#if generating}
    <p class="muted" aria-live="polite">
      Scoring frameworks and valuations from cached fundamentals — usually under
      a minute.
    </p>
  {/if}

  {#if loading && !dashboard}
    <p class="muted">Loading thesis…</p>
  {:else if dashboard == null}
    {#if !loading}
      <p class="empty">
        No thesis table yet. Generate to score Held and Watched names against
        the Graham Deep Value and Financial Strength frameworks.
      </p>
    {/if}
  {:else if emptyUniverse}
    <p class="empty">
      {dashboard.empty_message ??
        "Add tickers on Watchlist to build the Thesis table."}
    </p>
    <button type="button" class="goto" onclick={() => onnavigate("watchlist")}>
      Go to Watchlist
    </button>
  {:else}
    {#if dashboard.gaps.length > 0}
      <details class="gaps-box">
        <summary>{dashboard.gaps.length} data gaps</summary>
        <ul class="gaps">
          {#each dashboard.gaps as gap (gap)}
            <li>{gap}</li>
          {/each}
        </ul>
      </details>
    {/if}

    <section class="block" aria-labelledby="score-table-heading">
      <h2 id="score-table-heading">Framework scores</h2>
      <p class="hint">
        Select a ticker to see its per-check scorecards. “—” means
        insufficient data — never invented.
      </p>
      <FrameworkScoreTable
        tickers={dashboard.tickers}
        frameworks={dashboard.frameworks}
        selected={selectedTicker}
        {onselect}
      />
    </section>

    {#if selectedRow}
      <section class="block" aria-labelledby="scorecards-heading">
        <h2 id="scorecards-heading">
          {selectedRow.ticker}
          {#if selectedRow.name}
            <span class="company">— {selectedRow.name}</span>
          {/if}
        </h2>
        {#if selectedRow.sources_used.length > 0}
          <p class="hint">Sources: {selectedRow.sources_used.join(", ")}</p>
        {/if}
        <div class="cards">
          {#each selectedRow.frameworks as card (card.framework)}
            <FrameworkScorecard scorecard={card} />
          {/each}
        </div>
      </section>

      {#if selectedRow.margin_of_safety || selectedRow.valuation || selectedRow.assets}
        <section class="block" aria-labelledby="valuation-heading">
          <h2 id="valuation-heading">Valuation</h2>
          <p class="hint">
            Multiple simultaneous valuations and net-asset comparison. “—” means
            insufficient data.
          </p>
          <div class="cards">
            {#if selectedRow.margin_of_safety}
              <MarginOfSafety view={selectedRow.margin_of_safety} />
            {/if}
            {#if selectedRow.valuation}
              <ValuationLadder ladder={selectedRow.valuation.ladder} />
            {/if}
            {#if selectedRow.assets}
              <AssetBreakdown breakdown={selectedRow.assets} />
            {/if}
          </div>

          {#if selectedRow.valuation}
            <div class="method-schools">
              {#each [
                { key: "graham", label: "Graham", methods: selectedRow.valuation.graham },
                { key: "buffett", label: "Buffett", methods: selectedRow.valuation.buffett },
                { key: "modern", label: "Modern", methods: selectedRow.valuation.modern },
              ] as school (school.key)}
                <article class="method-panel" aria-label={`${school.label} valuations`}>
                  <h3>{school.label}</h3>
                  <table>
                    <thead>
                      <tr>
                        <th scope="col">Method</th>
                        <th scope="col">Value</th>
                      </tr>
                    </thead>
                    <tbody>
                      {#each school.methods as method (method.id)}
                        <tr>
                          <td>
                            <span class="check-name">{method.label}</span>
                            {#if method.detail}
                              <span class="detail">{method.detail}</span>
                            {/if}
                          </td>
                          <td
                            class="result"
                            class:na={method.value == null}
                          >
                            {formatValuationValue(method)}
                          </td>
                        </tr>
                      {/each}
                    </tbody>
                  </table>
                </article>
              {/each}
            </div>
          {/if}
        </section>
      {/if}
    {/if}
  {/if}

  <DisclaimerBar text={dashboard?.disclaimer ?? defaultDisclaimer} />
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
    margin-bottom: 1.5rem;
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
    max-width: 38rem;
    color: var(--ink-soft);
    font-size: 1.05rem;
    line-height: 1.4;
  }
  .actions {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.9rem;
    margin-bottom: 1rem;
  }
  .generate {
    border: 1px solid var(--ink);
    background: var(--ink);
    color: var(--paper);
    padding: 0.55rem 1.1rem;
    min-height: 44px;
    border-radius: 2px;
    font-weight: 500;
  }
  .generate:disabled {
    opacity: 0.6;
  }
  .meta {
    margin: 0;
    color: var(--ink-soft);
    font-size: 0.95rem;
  }
  .status {
    font-weight: 600;
    text-transform: lowercase;
  }
  .status-complete {
    color: var(--ok);
  }
  .status-partial {
    color: var(--partial);
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
  .gaps-box {
    margin: 0 0 1.25rem;
    color: var(--partial);
    font-size: 0.9rem;
  }
  .gaps-box summary {
    cursor: pointer;
    min-height: 44px;
    display: flex;
    align-items: center;
  }
  .gaps {
    margin: 0.25rem 0 0;
    padding-left: 1.1rem;
    line-height: 1.45;
  }
  .block {
    margin-bottom: 1.75rem;
  }
  .block h2 {
    margin: 0 0 0.4rem;
    font-family: var(--font-display);
    font-size: 1.35rem;
    font-weight: 600;
  }
  .company {
    color: var(--ink-soft);
    font-weight: 400;
    font-size: 1.05rem;
  }
  .hint {
    margin: 0 0 0.75rem;
    color: var(--ink-soft);
    font-size: 0.9rem;
  }
  .cards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(20rem, 1fr));
    gap: 1rem;
  }
  .method-schools {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(18rem, 1fr));
    gap: 1rem;
    margin-top: 1rem;
  }
  .method-panel {
    border: 1px solid var(--line);
    border-radius: 3px;
    padding: 1rem 1.1rem;
  }
  .method-panel h3 {
    margin: 0 0 0.55rem;
    font-family: var(--font-display);
    font-size: 1.05rem;
    font-weight: 600;
  }
  .method-panel table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.9rem;
  }
  .method-panel th,
  .method-panel td {
    text-align: left;
    padding: 0.4rem 0.25rem;
    border-bottom: 1px solid var(--line);
    vertical-align: top;
  }
  .method-panel th {
    color: var(--ink-soft);
    font-weight: 500;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }
  .check-name {
    display: block;
    font-weight: 500;
  }
  .detail {
    display: block;
    color: var(--ink-soft);
    font-size: 0.8rem;
    margin-top: 0.15rem;
  }
  .result {
    white-space: nowrap;
    font-weight: 600;
  }
  .result.na {
    color: var(--ink-soft);
    font-weight: 400;
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
