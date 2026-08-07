<script lang="ts">
  import { onMount, tick } from "svelte";
  import type { DecisionMapTarget } from "../../decisionMap";
  import { shouldCloseOnEscape } from "../../focusHelpers";
  import { formatValuationValue, thesisRowCoverage } from "../../thesisFormat";
  import type { ThesisTicker } from "../../types";
  import AdvisorInsightPanel from "./AdvisorInsight.svelte";
  import AssetBreakdown from "./AssetBreakdown.svelte";
  import FrameworkScorecard from "./FrameworkScorecard.svelte";
  import MarginOfSafety from "./MarginOfSafety.svelte";
  import OSScorecard from "./OSScorecard.svelte";
  import ResearchButton from "./ResearchButton.svelte";
  import ThesisTimeline from "./ThesisTimeline.svelte";
  import ValuationLadder from "./ValuationLadder.svelte";

  interface Props {
    row: ThesisTicker;
    /** Scroll this section into view when the drawer opens or focus changes. */
    focusSection?: DecisionMapTarget | null;
    onclose: () => void;
  }

  let { row, focusSection = null, onclose }: Props = $props();

  let panelEl: HTMLElement | undefined = $state();
  let closeBtn: HTMLButtonElement | undefined = $state();

  const coverage = $derived(thesisRowCoverage(row));

  function onKeydown(e: KeyboardEvent) {
    if (shouldCloseOnEscape(e.key)) {
      e.preventDefault();
      onclose();
    }
  }

  function drawerSectionId(section: DecisionMapTarget): string {
    return `thesis-drawer-${section}-heading`;
  }

  async function scrollFocus(section: DecisionMapTarget | null | undefined) {
    if (section == null || section === "brief") return;
    await tick();
    document.getElementById(drawerSectionId(section))?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  }

  onMount(() => {
    closeBtn?.focus();
    window.addEventListener("keydown", onKeydown);
    return () => window.removeEventListener("keydown", onKeydown);
  });

  $effect(() => {
    void scrollFocus(focusSection);
  });
</script>

<aside
  class="panel"
  bind:this={panelEl}
  aria-label={`${row.ticker} thesis detail`}
  aria-modal="true"
  role="dialog"
>
  <header>
    <div>
      <h2>{row.ticker}</h2>
      <p class="sub">
        {row.list_kind}{#if row.name}
          · {row.name}{/if}{#if row.sector}
          · {row.sector}{/if}
      </p>
      <p class="coverage coverage-{coverage.kind}" aria-live="polite">
        <span class="badge">{coverage.label}</span>
        {coverage.detail}
      </p>
    </div>
    <button
      type="button"
      class="close"
      bind:this={closeBtn}
      onclick={onclose}
      aria-label="Close thesis detail"
    >
      Close
    </button>
  </header>

  {#if coverage.kind === "thin"}
    <p class="thin-note" role="status">
      This ticker opened, but fundamentals are too thin to fill the engines.
      Regenerate after sources recover, or refresh research on Watchlist first.
    </p>
  {/if}

  <section aria-labelledby="thesis-drawer-frameworks-heading">
    <h3 id="thesis-drawer-frameworks-heading">How does each philosophy score this?</h3>
    {#if row.frameworks.length === 0}
      <p class="gap">No framework scorecards for this ticker.</p>
    {:else}
      <div class="stack">
        {#each row.frameworks as card (card.framework)}
          <FrameworkScorecard scorecard={card} />
        {/each}
        {#if row.os_score}
          <OSScorecard score={row.os_score} />
        {/if}
      </div>
    {/if}
  </section>

  <section aria-labelledby="thesis-drawer-valuation-heading">
    <h3 id="thesis-drawer-valuation-heading">Am I paying too much?</h3>
    {#if row.margin_of_safety || row.valuation || row.assets}
      <div class="stack">
        {#if row.margin_of_safety}
          <MarginOfSafety view={row.margin_of_safety} />
        {/if}
        {#if row.valuation}
          <ValuationLadder ladder={row.valuation.ladder} />
        {/if}
        {#if row.assets}
          <AssetBreakdown breakdown={row.assets} />
        {/if}
      </div>

      {#if row.valuation}
        <div class="method-schools">
          {#each [
            { key: "graham", label: "Graham", methods: row.valuation.graham },
            { key: "buffett", label: "Buffett", methods: row.valuation.buffett },
            { key: "modern", label: "Modern", methods: row.valuation.modern },
          ] as school (school.key)}
            <div class="method-panel" aria-label={`${school.label} valuations`}>
              <h4>{school.label}</h4>
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
                      <td class="result" class:na={method.value == null}>
                        {formatValuationValue(method)}
                      </td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>
          {/each}
        </div>
      {/if}
    {:else}
      <p class="gap">
        Valuation Engine — insufficient data for this ticker. Blanks stay honest.
      </p>
    {/if}
  </section>

  <section aria-labelledby="thesis-drawer-monitoring-heading">
    <h3 id="thesis-drawer-monitoring-heading">Has my thesis changed?</h3>
    {#if row.monitoring}
      <ThesisTimeline monitoring={row.monitoring} />
    {:else}
      <p class="gap">
        No thesis-change snapshot yet. Generate again after this ticker has a
        baseline.
      </p>
    {/if}
  </section>

  <section aria-labelledby="thesis-drawer-advisor-heading">
    <h3 id="thesis-drawer-advisor-heading">Buy more, hold, trim, or research further?</h3>
    <div class="stack">
      {#if row.advisor}
        <AdvisorInsightPanel insight={row.advisor} />
      {:else}
        <p class="gap">
          Advisor conclusion appears after Generate when enough signals exist.
        </p>
      {/if}
      <ResearchButton ticker={row.ticker} />
    </div>
  </section>
</aside>

<style>
  .panel {
    position: fixed;
    top: 0;
    right: 0;
    width: min(32rem, 100%);
    height: 100vh;
    overflow: auto;
    background: var(--paper);
    border-left: 1px solid var(--line);
    box-shadow: var(--shadow);
    padding: 1.25rem 1.35rem 2.5rem;
    animation: slide 0.28s ease;
    z-index: 20;
  }
  @keyframes slide {
    from {
      transform: translateX(12px);
      opacity: 0.6;
    }
    to {
      transform: none;
      opacity: 1;
    }
  }
  header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 1rem;
    margin-bottom: 1rem;
    padding-bottom: 0.85rem;
    border-bottom: 1px solid var(--line);
  }
  h2 {
    margin: 0;
    font-family: var(--font-display);
    font-size: 1.85rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    line-height: 1.1;
  }
  .sub {
    margin: 0.3rem 0 0;
    color: var(--ink-soft);
    font-size: 0.85rem;
  }
  .coverage {
    margin: 0.55rem 0 0;
    font-size: 0.82rem;
    line-height: 1.4;
    color: var(--ink-soft);
  }
  .badge {
    display: inline-block;
    margin-right: 0.35rem;
    font-weight: 600;
    text-transform: lowercase;
    letter-spacing: 0.02em;
  }
  .coverage-ok .badge {
    color: var(--ok);
  }
  .coverage-partial .badge {
    color: var(--partial);
  }
  .coverage-thin .badge {
    color: var(--error);
  }
  .close {
    border: 1px solid var(--line);
    background: white;
    border-radius: 2px;
    padding: 0.4rem 0.7rem;
    min-height: 40px;
    min-width: 44px;
    font-weight: 500;
    flex-shrink: 0;
  }
  .close:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }
  .thin-note {
    margin: 0 0 1rem;
    padding: 0.65rem 0.75rem;
    background: rgba(184, 134, 11, 0.1);
    color: var(--ink-soft);
    font-size: 0.88rem;
    line-height: 1.4;
    border-radius: 2px;
  }
  section {
    margin-bottom: 1.35rem;
  }
  h3 {
    margin: 0 0 0.55rem;
    font-family: var(--font-display);
    font-size: 1.05rem;
    font-weight: 600;
    line-height: 1.3;
  }
  .stack {
    display: grid;
    gap: 0.75rem;
  }
  .gap {
    margin: 0;
    color: var(--ink-soft);
    font-size: 0.9rem;
    line-height: 1.45;
  }
  .method-schools {
    display: grid;
    gap: 0.75rem;
    margin-top: 0.75rem;
  }
  .method-panel {
    border: 1px solid var(--line);
    border-radius: 2px;
    padding: 0.75rem 0.85rem;
  }
  .method-panel h4 {
    margin: 0 0 0.45rem;
    font-family: var(--font-display);
    font-size: 0.95rem;
    font-weight: 600;
  }
  .method-panel table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.85rem;
  }
  .method-panel th,
  .method-panel td {
    text-align: left;
    padding: 0.35rem 0.2rem;
    border-bottom: 1px solid var(--line);
    vertical-align: top;
  }
  .method-panel th {
    color: var(--ink-soft);
    font-weight: 500;
    font-size: 0.7rem;
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
    font-size: 0.78rem;
    margin-top: 0.1rem;
  }
  .result {
    white-space: nowrap;
    font-weight: 600;
  }
  .result.na {
    color: var(--ink-soft);
    font-weight: 400;
  }
  @media (max-width: 720px) {
    .panel {
      width: 100%;
    }
  }
</style>
