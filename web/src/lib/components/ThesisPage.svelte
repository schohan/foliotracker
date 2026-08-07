<script lang="ts">
  import { onMount, tick } from "svelte";
  import { fetchThesis, generateThesis } from "../api";
  import type { DecisionMapTarget } from "../decisionMap";
  import { rowFocusId } from "../focusHelpers";
  import {
    healthBucketMeta,
    tickersForHealthBucket,
    type PortfolioHealthBucket,
  } from "../portfolioHealth";
  import type { AppView, ThesisDashboard } from "../types";
  import DisclaimerBar from "./DisclaimerBar.svelte";
  import PrimaryNav from "./PrimaryNav.svelte";
  import DecisionMap from "./thesis/DecisionMap.svelte";
  import FrameworkScoreTable from "./thesis/FrameworkScoreTable.svelte";
  import PortfolioHealth from "./thesis/PortfolioHealth.svelte";
  import ThesisDrawer from "./thesis/ThesisDrawer.svelte";

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
  let drawerFocus = $state<DecisionMapTarget | null>(null);
  let healthBucket = $state<PortfolioHealthBucket | null>(null);

  const emptyUniverse = $derived(
    dashboard != null && dashboard.universe_count === 0,
  );
  const selectedRow = $derived(
    dashboard?.tickers.find((t) => t.ticker === selectedTicker) ?? null,
  );
  const thinCount = $derived(
    dashboard?.tickers.filter((t) => {
      const scored = t.frameworks.some((f) => f.score != null);
      const rich =
        t.valuation != null ||
        t.margin_of_safety != null ||
        t.advisor != null ||
        t.monitoring != null;
      return !scored && !rich;
    }).length ?? 0,
  );
  const healthFilterTickers = $derived(
    healthBucket != null && dashboard != null
      ? tickersForHealthBucket(dashboard.tickers, healthBucket).map(
          (t) => t.ticker,
        )
      : null,
  );
  const healthFilterLabel = $derived(
    healthBucket != null ? healthBucketMeta(healthBucket).label : null,
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
        drawerFocus = null;
      }
      healthBucket = null;
    } catch (e) {
      loadError = e instanceof Error ? e.message : String(e);
    } finally {
      generating = false;
    }
  }

  function onselect(ticker: string) {
    if (selectedTicker === ticker) {
      selectedTicker = null;
      drawerFocus = null;
      return;
    }
    selectedTicker = ticker;
    drawerFocus = "frameworks";
  }

  function onopenFromHealth(ticker: string) {
    selectedTicker = ticker;
    drawerFocus = "frameworks";
    void tick().then(() => {
      document
        .getElementById("frameworks-heading")
        ?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }

  function oncloseDrawer() {
    const prev = selectedTicker;
    selectedTicker = null;
    drawerFocus = null;
    if (prev) {
      void tick().then(() => {
        document.getElementById(rowFocusId(prev))?.focus();
      });
    }
  }

  function onsection(target: Exclude<DecisionMapTarget, "brief">) {
    if (target === "fundamentals") {
      document
        .getElementById("fundamentals-heading")
        ?.scrollIntoView({ behavior: "smooth", block: "start" });
      return;
    }
    if (target === "frameworks") {
      if (selectedTicker == null) {
        document
          .getElementById("frameworks-heading")
          ?.scrollIntoView({ behavior: "smooth", block: "start" });
        return;
      }
      drawerFocus = "frameworks";
      return;
    }
    if (selectedTicker == null) {
      document
        .getElementById("frameworks-heading")
        ?.scrollIntoView({ behavior: "smooth", block: "start" });
      return;
    }
    drawerFocus = target;
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

<main class="page" class:drawer-open={selectedRow != null}>
  <header class="hero">
    <p class="brand">FolioTracker</p>
    <PrimaryNav {view} {onnavigate} />
    <p class="tag">
      Score every holding across philosophies — then open one ticker for
      valuation, thesis change, and advisor guidance.
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
        Graham Deep Value and Financial Strength.
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
    {#if dashboard.gaps.length > 0 || thinCount > 0}
      <details class="gaps-box" open={thinCount > 0 && thinCount === dashboard.tickers.length}>
        <summary>
          {#if thinCount > 0}
            {thinCount} ticker{thinCount === 1 ? "" : "s"} with thin data
            {#if dashboard.gaps.length > 0}
              · {dashboard.gaps.length} source gap{dashboard.gaps.length === 1
                ? ""
                : "s"}
            {/if}
          {:else}
            {dashboard.gaps.length} data gap{dashboard.gaps.length === 1
              ? ""
              : "s"}
          {/if}
        </summary>
        <p class="gaps-lead">
          Thin rows stay clickable. Open them to see honest blanks — never
          invented scores. Rate limits on Yahoo / SEC / Alpha Vantage often
          leave only partial fundamentals until the next Generate.
        </p>
        {#if dashboard.gaps.length > 0}
          <ul class="gaps">
            {#each dashboard.gaps as gap (gap)}
              <li>{gap}</li>
            {/each}
          </ul>
        {/if}
      </details>
    {/if}

    <DecisionMap
      selected={selectedRow}
      portfolio={dashboard.portfolio}
      {onnavigate}
      {onsection}
    />

    {#if dashboard.portfolio}
      <PortfolioHealth
        portfolio={dashboard.portfolio}
        tickers={dashboard.tickers}
        activeBucket={healthBucket}
        onbucket={(b) => (healthBucket = b)}
        onopenticker={onopenFromHealth}
      />
    {/if}

    <section class="block" aria-labelledby="frameworks-heading">
      <div class="block-head">
        <h2 id="frameworks-heading">How does each philosophy score this?</h2>
        <p class="hint">
          Investment Framework Engine — click a row for the full scorecard.
          Sort columns; “—” means insufficient data.
        </p>
      </div>
      <FrameworkScoreTable
        tickers={dashboard.tickers}
        frameworks={dashboard.frameworks}
        selected={selectedTicker}
        filterTickers={healthFilterTickers}
        filterLabel={healthFilterLabel}
        {onselect}
        onclearfilter={() => (healthBucket = null)}
      />
    </section>

    <section class="block planned" aria-labelledby="fundamentals-heading">
      <h2 id="fundamentals-heading">
        Is the company becoming stronger or weaker?
      </h2>
      <p class="hint">
        Fundamental Engine — planned. Merged fundamentals already feed other
        engines; dedicated stronger/weaker metrics ship next.
      </p>
    </section>
  {/if}

  <DisclaimerBar text={dashboard?.disclaimer ?? defaultDisclaimer} />
</main>

{#if selectedRow}
  <ThesisDrawer
    row={selectedRow}
    focusSection={drawerFocus}
    onclose={oncloseDrawer}
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
    transition: padding-right 0.2s ease;
  }
  .page.drawer-open {
    padding-right: min(33rem, 42vw);
  }
  @media (max-width: 960px) {
    .page.drawer-open {
      padding-right: 1.25rem;
    }
  }
  .hero {
    margin-bottom: 1.35rem;
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
  .generate:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
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
    border: 1px solid rgba(184, 134, 11, 0.35);
    border-radius: 2px;
    padding: 0 0.75rem;
    background: rgba(184, 134, 11, 0.06);
  }
  .gaps-box summary {
    cursor: pointer;
    min-height: 44px;
    display: flex;
    align-items: center;
    font-weight: 550;
    color: var(--ink);
  }
  .gaps-lead {
    margin: 0 0 0.5rem;
    color: var(--ink-soft);
    line-height: 1.45;
  }
  .gaps {
    margin: 0 0 0.75rem;
    padding-left: 1.1rem;
    line-height: 1.45;
    color: var(--ink-soft);
  }
  .block {
    margin-bottom: 1.75rem;
  }
  .block-head {
    margin-bottom: 0.35rem;
  }
  .block.planned h2 {
    color: var(--ink-soft);
  }
  .block.planned .hint {
    font-style: italic;
  }
  .block h2 {
    margin: 0 0 0.35rem;
    font-family: var(--font-display);
    font-size: 1.35rem;
    font-weight: 600;
  }
  .hint {
    margin: 0 0 0.75rem;
    color: var(--ink-soft);
    font-size: 0.9rem;
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
