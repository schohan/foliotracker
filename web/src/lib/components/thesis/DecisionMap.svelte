<script lang="ts">
  import {
    buildDecisionMapRows,
    type DecisionMapTarget,
  } from "../../decisionMap";
  import type { AppView, PortfolioHealthRollup, ThesisTicker } from "../../types";

  interface Props {
    selected: ThesisTicker | null;
    portfolio: PortfolioHealthRollup | null;
    onnavigate: (view: AppView) => void;
    /** Jump to a thesis section (table or drawer). Brief still uses onnavigate. */
    onsection?: (target: Exclude<DecisionMapTarget, "brief">) => void;
  }

  let { selected, portfolio, onnavigate, onsection }: Props = $props();

  const rows = $derived(buildDecisionMapRows(selected, portfolio));

  function onActivate(target: DecisionMapTarget) {
    if (target === "brief") {
      onnavigate("brief");
      return;
    }
    if (onsection) {
      onsection(target);
      return;
    }
    const el = document.getElementById(`${target}-heading`);
    el?.scrollIntoView({ behavior: "smooth", block: "start" });
  }
</script>

<section class="map" aria-labelledby="decision-map-heading">
  <header>
    <h2 id="decision-map-heading">Decision Map</h2>
    <p class="meta">
      {#if selected}
        Answers for <strong>{selected.ticker}</strong>. Jump to a question to
        open detail.
      {:else}
        Portfolio rollup until you select a ticker in the table below.
      {/if}
    </p>
  </header>

  <dl class="rows">
    {#each rows as row (row.id)}
      <div class="row" class:planned={row.planned} class:needs={row.needsTicker}>
        <dt>
          <button
            type="button"
            class="jump"
            onclick={() => onActivate(row.id)}
          >
            {row.question}
          </button>
        </dt>
        <dd>
          <button
            type="button"
            class="answer"
            class:planned={row.planned}
            class:soft={row.needsTicker}
            onclick={() => onActivate(row.id)}
          >
            {row.answer}
          </button>
        </dd>
      </div>
    {/each}
  </dl>
</section>

<style>
  .map {
    margin: 0 0 1.35rem;
    padding-bottom: 1.15rem;
    border-bottom: 1px solid var(--line);
  }
  header {
    margin-bottom: 0.65rem;
  }
  h2 {
    margin: 0;
    font-family: var(--font-display);
    font-size: 1.25rem;
    font-weight: 600;
  }
  .meta {
    margin: 0.25rem 0 0;
    color: var(--ink-soft);
    font-size: 0.85rem;
  }
  .meta strong {
    color: var(--ink);
    font-weight: 600;
  }
  .rows {
    margin: 0;
  }
  .row {
    display: grid;
    grid-template-columns: minmax(0, 1.5fr) minmax(0, 1fr);
    gap: 0.65rem 1rem;
    align-items: baseline;
    padding: 0.45rem 0;
    border-bottom: 1px solid var(--line);
    font-size: 0.9rem;
  }
  .row:last-child {
    border-bottom: none;
  }
  dt {
    margin: 0;
    min-width: 0;
  }
  dd {
    margin: 0;
    text-align: right;
    min-width: 0;
  }
  .jump,
  .answer {
    appearance: none;
    background: none;
    border: none;
    padding: 0.15rem 0;
    margin: 0;
    font: inherit;
    color: inherit;
    cursor: pointer;
    text-align: inherit;
    max-width: 100%;
    min-height: 44px;
  }
  .jump {
    color: var(--ink-soft);
    font-weight: 400;
    text-align: left;
  }
  .jump:hover,
  .jump:focus-visible,
  .answer:hover,
  .answer:focus-visible {
    color: var(--accent);
    outline: none;
  }
  .jump:focus-visible,
  .answer:focus-visible {
    text-decoration: underline;
    text-underline-offset: 3px;
  }
  .answer {
    font-family: var(--font-display);
    font-weight: 600;
    color: var(--ink);
  }
  .answer.planned,
  .answer.soft {
    font-weight: 500;
    color: var(--ink-soft);
  }
  .row.planned .jump {
    font-style: italic;
  }
  @media (max-width: 640px) {
    .row {
      grid-template-columns: 1fr;
      gap: 0.1rem;
    }
    dd {
      text-align: left;
    }
    .jump,
    .answer {
      min-height: 36px;
    }
  }
</style>
