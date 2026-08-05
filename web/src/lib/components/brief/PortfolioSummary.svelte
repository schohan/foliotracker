<script lang="ts">
  import type { BriefSummary, BriefInsightMode } from "../../types";

  interface Props {
    summary: BriefSummary;
    generatedAt: string;
    insightMode: BriefInsightMode;
    generationStatus: string;
  }

  let { summary, generatedAt, insightMode, generationStatus }: Props = $props();

  function formatWhen(iso: string): string {
    try {
      return new Date(iso).toLocaleString(undefined, {
        dateStyle: "full",
        timeStyle: "short",
      });
    } catch {
      return iso;
    }
  }
</script>

<section class="summary" aria-labelledby="brief-summary-heading">
  <div class="top">
    <div>
      <h2 id="brief-summary-heading">Portfolio Daily Brief</h2>
      <p class="meta">
        {formatWhen(generatedAt)} · {summary.holdings_count} holdings ·
        <span class="status">{generationStatus}</span>
        · insight {insightMode}
      </p>
    </div>
  </div>

  <div class="counts" role="group" aria-label="Priority counts">
    <div class="stat high">
      <span class="n">{summary.high_count}</span>
      <span class="l">High priority</span>
    </div>
    <div class="stat med">
      <span class="n">{summary.medium_count}</span>
      <span class="l">Medium</span>
    </div>
    <div class="stat quiet">
      <span class="n">{summary.quiet_count}</span>
      <span class="l">Nothing important</span>
    </div>
  </div>

  <div class="sentiment" aria-label="Sentiment counts">
    <span>Positive {summary.positive_count}</span>
    <span>Negative {summary.negative_count}</span>
    <span>Neutral {summary.neutral_count}</span>
    <span class="risk">Market risk · {summary.market_risk}</span>
  </div>

  {#if summary.themes.length > 0}
    <p class="themes">
      Themes ·
      {#each summary.themes as t, i (t)}
        {t}{i < summary.themes.length - 1 ? " · " : ""}
      {/each}
    </p>
  {/if}

  {#if summary.biggest_story || summary.biggest_risk || summary.biggest_opportunity}
    <dl class="digest">
      {#if summary.biggest_story}
        <div><dt>Biggest story</dt><dd>{summary.biggest_story}</dd></div>
      {/if}
      {#if summary.biggest_risk}
        <div><dt>Biggest risk</dt><dd>{summary.biggest_risk}</dd></div>
      {/if}
      {#if summary.biggest_opportunity}
        <div><dt>Biggest opportunity</dt><dd>{summary.biggest_opportunity}</dd></div>
      {/if}
    </dl>
  {/if}
</section>

<style>
  .summary {
    margin: 0 0 1.25rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid var(--line);
  }
  h2 {
    margin: 0;
    font-family: var(--font-display);
    font-size: 1.35rem;
    font-weight: 600;
  }
  .meta {
    margin: 0.35rem 0 0;
    color: var(--ink-soft);
    font-size: 0.88rem;
  }
  .status {
    text-transform: uppercase;
    letter-spacing: 0.04em;
    font-size: 0.72rem;
    font-weight: 600;
  }
  .counts {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.75rem;
    margin: 1rem 0 0.75rem;
  }
  .stat {
    padding: 0.65rem 0.75rem;
    border: 1px solid var(--line);
    border-radius: 2px;
    background: rgba(255, 255, 255, 0.55);
  }
  .stat .n {
    display: block;
    font-family: var(--font-display);
    font-size: 1.6rem;
    font-weight: 600;
    line-height: 1.1;
  }
  .stat .l {
    font-size: 0.78rem;
    color: var(--ink-soft);
  }
  .stat.high .n {
    color: var(--error);
  }
  .stat.quiet .n {
    color: var(--ok);
  }
  .sentiment {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem 1.25rem;
    font-size: 0.85rem;
    color: var(--ink-soft);
  }
  .risk {
    color: var(--ink);
    font-weight: 500;
  }
  .themes {
    margin: 0.65rem 0 0;
    font-size: 0.85rem;
    color: var(--ink-soft);
  }
  .digest {
    margin: 0.85rem 0 0;
    display: grid;
    gap: 0.45rem;
  }
  .digest div {
    display: grid;
    grid-template-columns: 9rem 1fr;
    gap: 0.5rem;
    font-size: 0.88rem;
  }
  .digest dt {
    color: var(--ink-soft);
    font-weight: 500;
  }
  .digest dd {
    margin: 0;
  }
  @media (max-width: 640px) {
    .counts {
      grid-template-columns: 1fr;
    }
    .digest div {
      grid-template-columns: 1fr;
      gap: 0.15rem;
    }
  }
</style>
