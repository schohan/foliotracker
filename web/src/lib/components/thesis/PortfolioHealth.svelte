<script lang="ts">
  import {
    PORTFOLIO_HEALTH_BUCKETS,
    healthBucketMeta,
    tickersForHealthBucket,
    type PortfolioHealthBucket,
  } from "../../portfolioHealth";
  import { formatFrameworkScore, formatOsRating } from "../../thesisFormat";
  import type { PortfolioHealthRollup, ThesisTicker } from "../../types";
  import HelpTip from "./HelpTip.svelte";

  interface Props {
    portfolio: PortfolioHealthRollup;
    tickers: ThesisTicker[];
    activeBucket: PortfolioHealthBucket | null;
    onbucket: (bucket: PortfolioHealthBucket | null) => void;
    onopenticker: (ticker: string) => void;
  }

  let {
    portfolio,
    tickers,
    activeBucket,
    onbucket,
    onopenticker,
  }: Props = $props();

  const matches = $derived(
    activeBucket != null
      ? tickersForHealthBucket(tickers, activeBucket)
      : [],
  );
  const activeMeta = $derived(
    activeBucket != null ? healthBucketMeta(activeBucket) : null,
  );

  function toggle(bucket: PortfolioHealthBucket) {
    onbucket(activeBucket === bucket ? null : bucket);
  }
</script>

<section class="health" aria-labelledby="portfolio-health-heading">
  <header>
    <div>
      <h2 id="portfolio-health-heading">
        Portfolio Health
        <HelpTip
          entry={{
            title: "Portfolio Health",
            what: "Roll-up counts of how many holdings match common research flags.",
            how: "Each count uses the same rules as the Investment OS / valuation engines (for example balance-sheet points ≥ 70 for Strong Balance Sheets).",
            why: "Click a count to see exactly which tickers drive it — then open one for the full thesis.",
          }}
        />
      </h2>
      <p class="meta">
        Mean Investment OS Score across {portfolio.tickers_scored} scored
        ticker{portfolio.tickers_scored === 1 ? "" : "s"}
      </p>
    </div>
    <div class="score-block" aria-label="Portfolio health score">
      <span class="score" class:na={portfolio.health_score == null}>
        {formatFrameworkScore(portfolio.health_score)}
      </span>
      {#if portfolio.health_rating}
        <span class="rating rating-{portfolio.health_rating.toLowerCase()}">
          {formatOsRating(portfolio.health_rating)}
        </span>
      {/if}
    </div>
  </header>

  <ul class="counts">
    {#each PORTFOLIO_HEALTH_BUCKETS as row (row.key)}
      {@const count = Number(portfolio[row.key])}
      <li>
        <button
          type="button"
          class="count-btn"
          class:active={activeBucket === row.key}
          class:empty={count === 0}
          aria-pressed={activeBucket === row.key}
          disabled={count === 0}
          onclick={() => toggle(row.key)}
        >
          <span class="label">{row.label}</span>
          <span class="num">{count}</span>
        </button>
      </li>
    {/each}
  </ul>

  {#if activeMeta}
    <div class="filter" aria-live="polite">
      <div class="filter-head">
        <p class="filter-title">
          Showing {matches.length} · {activeMeta.label}
        </p>
        <button type="button" class="clear" onclick={() => onbucket(null)}>
          Clear
        </button>
      </div>
      <p class="filter-explain">{activeMeta.explain}</p>
      {#if matches.length === 0}
        <p class="muted">No matching tickers in this Generate.</p>
      {:else}
        <ul class="chips">
          {#each matches as row (row.ticker)}
            <li>
              <button
                type="button"
                class="chip"
                onclick={() => onopenticker(row.ticker)}
              >
                {row.ticker}
              </button>
            </li>
          {/each}
        </ul>
      {/if}
    </div>
  {/if}
</section>

<style>
  .health {
    margin: 0 0 1.5rem;
    padding-bottom: 1.25rem;
    border-bottom: 1px solid var(--line);
  }
  header {
    display: flex;
    flex-wrap: wrap;
    align-items: flex-end;
    justify-content: space-between;
    gap: 0.75rem 1.25rem;
    margin-bottom: 0.9rem;
  }
  h2 {
    margin: 0;
    font-family: var(--font-display);
    font-size: 1.35rem;
    font-weight: 600;
    display: inline-flex;
    align-items: center;
    gap: 0.15rem;
  }
  .meta {
    margin: 0.25rem 0 0;
    color: var(--ink-soft);
    font-size: 0.85rem;
  }
  .score-block {
    display: flex;
    align-items: baseline;
    gap: 0.55rem;
  }
  .score {
    font-family: var(--font-display);
    font-size: 2.4rem;
    font-weight: 700;
    line-height: 1;
  }
  .score.na {
    color: var(--ink-soft);
    font-weight: 400;
  }
  .rating {
    font-weight: 600;
    font-size: 0.95rem;
  }
  .rating-excellent,
  .rating-good {
    color: var(--ok);
  }
  .rating-fair {
    color: var(--ink);
  }
  .rating-weak,
  .rating-poor {
    color: var(--partial);
  }
  .counts {
    margin: 0;
    padding: 0;
    list-style: none;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr));
    gap: 0.35rem 0.75rem;
  }
  .count-btn {
    width: 100%;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 0.75rem;
    padding: 0.45rem 0.35rem;
    min-height: 44px;
    border: none;
    border-bottom: 1px solid var(--line);
    border-radius: 0;
    background: transparent;
    font: inherit;
    color: inherit;
    cursor: pointer;
    text-align: left;
  }
  .count-btn:hover:not(:disabled),
  .count-btn:focus-visible {
    color: var(--accent);
    outline: none;
    background: var(--accent-soft);
  }
  .count-btn.active {
    background: var(--accent-soft);
    box-shadow: inset 3px 0 0 var(--accent);
    font-weight: 550;
  }
  .count-btn:disabled,
  .count-btn.empty {
    opacity: 0.55;
    cursor: default;
  }
  .label {
    color: var(--ink-soft);
    font-size: 0.9rem;
  }
  .count-btn.active .label,
  .count-btn:hover:not(:disabled) .label {
    color: inherit;
  }
  .num {
    font-weight: 700;
    font-variant-numeric: tabular-nums;
  }
  .filter {
    margin-top: 0.85rem;
    padding: 0.75rem 0.85rem;
    border: 1px solid var(--line);
    border-radius: 2px;
    background: rgba(196, 92, 38, 0.05);
  }
  .filter-head {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
  }
  .filter-title {
    margin: 0;
    font-weight: 600;
    font-size: 0.95rem;
  }
  .clear {
    border: 1px solid var(--line);
    background: white;
    border-radius: 2px;
    padding: 0.35rem 0.65rem;
    min-height: 36px;
    font-weight: 500;
    cursor: pointer;
  }
  .clear:hover,
  .clear:focus-visible {
    border-color: var(--accent);
    color: var(--accent);
    outline: none;
  }
  .filter-explain {
    margin: 0.4rem 0 0.65rem;
    color: var(--ink-soft);
    font-size: 0.85rem;
    line-height: 1.4;
  }
  .muted {
    margin: 0;
    color: var(--ink-soft);
    font-size: 0.85rem;
  }
  .chips {
    margin: 0;
    padding: 0;
    list-style: none;
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
  }
  .chip {
    border: 1px solid var(--ink);
    background: var(--ink);
    color: var(--paper);
    border-radius: 2px;
    padding: 0.35rem 0.65rem;
    min-height: 36px;
    font-family: var(--font-display);
    font-weight: 600;
    cursor: pointer;
  }
  .chip:hover,
  .chip:focus-visible {
    background: var(--accent);
    border-color: var(--accent);
    outline: none;
  }
</style>
