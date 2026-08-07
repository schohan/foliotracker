<script lang="ts">
  import { formatFrameworkScore, formatOsRating } from "../../thesisFormat";
  import type { PortfolioHealthRollup } from "../../types";

  interface Props {
    portfolio: PortfolioHealthRollup;
  }

  let { portfolio }: Props = $props();

  const counts: { key: keyof PortfolioHealthRollup; label: string }[] = [
    { key: "strong_balance_sheets", label: "Strong Balance Sheets" },
    { key: "weak_balance_sheets", label: "Weak Balance Sheets" },
    { key: "potential_value_traps", label: "Potential Value Traps" },
    { key: "significantly_undervalued", label: "Significantly Undervalued" },
    { key: "overvalued", label: "Overvalued" },
    { key: "high_conviction", label: "High Conviction" },
    { key: "thesis_broken", label: "Thesis Broken" },
  ];
</script>

<section class="health" aria-labelledby="portfolio-health-heading">
  <header>
    <div>
      <h2 id="portfolio-health-heading">Portfolio Health</h2>
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

  <dl class="counts">
    {#each counts as row (row.key)}
      <div>
        <dt>{row.label}</dt>
        <dd>{Number(portfolio[row.key])}</dd>
      </div>
    {/each}
  </dl>
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
  .rating-excellent {
    color: var(--ok);
  }
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
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr));
    gap: 0.45rem 1rem;
  }
  .counts > div {
    display: flex;
    justify-content: space-between;
    gap: 0.75rem;
    padding: 0.35rem 0;
    border-bottom: 1px solid var(--line);
    font-size: 0.9rem;
  }
  dt {
    color: var(--ink-soft);
    font-weight: 400;
  }
  dd {
    margin: 0;
    font-weight: 600;
  }
</style>
