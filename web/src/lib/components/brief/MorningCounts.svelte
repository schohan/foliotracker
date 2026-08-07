<script lang="ts">
  import type { BriefMorningCounts } from "../../types";

  interface Props {
    morning: BriefMorningCounts;
  }

  let { morning }: Props = $props();

  const rows: { key: keyof BriefMorningCounts; label: string }[] = [
    { key: "thesis_changed", label: "Thesis Changed" },
    { key: "valuation_improved", label: "Valuation Improved" },
    { key: "mos_increased", label: "Margin of Safety Increased" },
    { key: "balance_sheet_weakened", label: "Balance Sheet Weakened" },
    { key: "risk_increased", label: "Risk Increased" },
  ];

  function oppLabel(score: BriefMorningCounts["opportunity_score"]): string {
    if (!score) return "—";
    return score.charAt(0).toUpperCase() + score.slice(1);
  }
</script>

<section class="morning" aria-labelledby="morning-heading">
  <h3 id="morning-heading">Today's Portfolio</h3>
  {#if !morning.thesis_available}
    <p class="hint">Generate Thesis to populate these counts.</p>
  {/if}
  <dl class="counts">
    {#each rows as row (row.key)}
      <div>
        <dt>{row.label}</dt>
        <dd>{Number(morning[row.key])}</dd>
      </div>
    {/each}
    <div class="opp">
      <dt>Opportunity Score</dt>
      <dd class:high={morning.opportunity_score === "high"}
          class:low={morning.opportunity_score === "low"}
          class:med={morning.opportunity_score === "medium"}>
        {oppLabel(morning.opportunity_score)}
      </dd>
    </div>
  </dl>
</section>

<style>
  .morning {
    margin: 0 0 1.25rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid var(--line);
  }
  h3 {
    margin: 0;
    font-family: var(--font-display);
    font-size: 1.05rem;
    font-weight: 600;
  }
  .hint {
    margin: 0.35rem 0 0;
    font-size: 0.82rem;
    color: var(--ink-soft);
  }
  .counts {
    margin: 0.75rem 0 0;
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.55rem 1rem;
  }
  .counts div {
    display: flex;
    justify-content: space-between;
    gap: 0.75rem;
    font-size: 0.88rem;
    padding: 0.35rem 0;
    border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  }
  dt {
    color: var(--ink-soft);
    font-weight: 500;
  }
  dd {
    margin: 0;
    font-family: var(--font-display);
    font-weight: 600;
  }
  .opp dd.high {
    color: var(--ok);
  }
  .opp dd.low {
    color: var(--error);
  }
  .opp dd.med {
    color: var(--ink);
  }
  @media (max-width: 640px) {
    .counts {
      grid-template-columns: 1fr;
    }
  }
</style>
