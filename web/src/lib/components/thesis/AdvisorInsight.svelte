<script lang="ts">
  import { formatAdvisorConclusion, formatAdvisorConfidence } from "../../thesisFormat";
  import type { AdvisorInsight } from "../../types";

  interface Props {
    insight: AdvisorInsight;
  }

  let { insight }: Props = $props();
</script>

<article class="panel advisor" aria-label="AI Portfolio Advisor">
  <header>
    <h3>Today's Insight</h3>
    <p class="provider">Provider: {insight.provider}</p>
  </header>

  <ul class="reasoning">
    {#each insight.reasoning as line (line)}
      <li>{line}</li>
    {/each}
  </ul>

  <p class="conclusion conclusion-{insight.conclusion}">
    {insight.conclusion_label || formatAdvisorConclusion(insight.conclusion)}
  </p>
  <p class="confidence">
    Confidence: {formatAdvisorConfidence(insight.confidence)}
  </p>
  <p class="scope">
    Directive guidance appears only here. Still not a substitute for your own
    research.
  </p>
</article>

<style>
  .panel {
    border: 1px solid var(--line);
    border-radius: 3px;
    padding: 1rem 1.1rem;
  }
  .advisor {
    border-color: var(--accent, var(--line));
  }
  header {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    justify-content: space-between;
    gap: 0.5rem;
    margin-bottom: 0.75rem;
  }
  h3 {
    margin: 0;
    font-family: var(--font-display);
    font-size: 1.1rem;
    font-weight: 600;
  }
  .provider {
    margin: 0;
    color: var(--ink-soft);
    font-size: 0.85rem;
  }
  .reasoning {
    margin: 0 0 0.85rem;
    padding-left: 1.1rem;
    line-height: 1.45;
  }
  .conclusion {
    margin: 0 0 0.35rem;
    font-family: var(--font-display);
    font-size: 1.35rem;
    font-weight: 700;
  }
  .conclusion-buy_more {
    color: var(--ok);
  }
  .conclusion-hold {
    color: var(--ink);
  }
  .conclusion-trim {
    color: var(--partial);
  }
  .conclusion-research_further {
    color: var(--partial);
  }
  .conclusion-wait {
    color: var(--ink-soft);
  }
  .confidence {
    margin: 0 0 0.5rem;
    font-weight: 600;
    font-size: 0.95rem;
  }
  .scope {
    margin: 0;
    color: var(--ink-soft);
    font-size: 0.8rem;
    line-height: 1.4;
  }
</style>
