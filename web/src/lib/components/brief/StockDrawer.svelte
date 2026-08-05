<script lang="ts">
  import { onMount } from "svelte";
  import type { BriefTicker, Phase0Result } from "../../types";
  import { shouldCloseOnEscape } from "../../focusHelpers";
  import SourceList from "./SourceList.svelte";

  interface Props {
    row: BriefTicker;
    research: Phase0Result | null;
    researchLoading: boolean;
    researchError: string | null;
    onclose: () => void;
  }

  let { row, research, researchLoading, researchError, onclose }: Props = $props();

  let panelEl: HTMLElement | undefined = $state();
  let closeBtn: HTMLButtonElement | undefined = $state();

  function formatPct(v: number | null | undefined): string {
    if (v == null || Number.isNaN(v)) return "—";
    const pct = v * 100;
    const sign = pct > 0 ? "+" : "";
    return `${sign}${pct.toFixed(1)}%`;
  }

  function onKeydown(e: KeyboardEvent) {
    if (shouldCloseOnEscape(e.key)) {
      e.preventDefault();
      onclose();
    }
  }

  onMount(() => {
    closeBtn?.focus();
    window.addEventListener("keydown", onKeydown);
    return () => window.removeEventListener("keydown", onKeydown);
  });
</script>

<div
  class="panel"
  bind:this={panelEl}
  aria-label="Stock brief drawer"
  aria-modal="true"
  role="dialog"
>
  <header>
    <div>
      <h2>{row.ticker}</h2>
      <p class="sub">
        {row.list_kind} · impact {row.impact_score}
        {#if row.priority}
          · {row.priority}
        {/if}
        · {formatPct(row.daily_return)}
      </p>
    </div>
    <button type="button" class="close" bind:this={closeBtn} onclick={onclose} aria-label="Close">
      Close
    </button>
  </header>

  <section>
    <h3>Summary</h3>
    <p>{row.headline ?? "Material activity"}</p>
    {#if row.suggested_action}
      <p class="action">{row.suggested_action}</p>
    {/if}
  </section>

  <section>
    <h3>Events</h3>
    {#each row.bullets as b (b.event_key)}
      <article class="ev">
        <p class="h">{b.headline}</p>
        <p class="o">{b.one_line_summary}</p>
        <p class="meta">
          Impact {b.impact_score} · {b.sentiment} · conf {b.confidence}
        </p>
        {#if b.insight}
          <p class="explain">{b.insight.explain_busy}</p>
        {/if}
        <SourceList sources={b.sources} />
      </article>
    {/each}
  </section>

  {#if row.insight}
    <section>
      <h3>AI opinion · {row.insight.provider}</h3>
      <dl>
        <div><dt>What happened</dt><dd>{row.insight.what_happened}</dd></div>
        <div><dt>Why</dt><dd>{row.insight.why}</dd></div>
        <div><dt>Care?</dt><dd>{row.insight.should_long_term_care}</dd></div>
      </dl>
    </section>
  {/if}

  <section>
    <h3>Metrics</h3>
    <p class="muted">
      P/E {row.trailing_pe != null ? row.trailing_pe.toFixed(1) : "—"} · 1Y
      {formatPct(row.return_1y)} · G
      {row.growth_score != null ? row.growth_score.toFixed(0) : "—"} / V
      {row.value_score != null ? row.value_score.toFixed(0) : "—"} / R
      {row.risk_score != null ? row.risk_score.toFixed(0) : "—"}
    </p>
  </section>

  <section>
    <h3>Research</h3>
    {#if researchLoading}
      <p class="muted">Loading Phase0…</p>
    {:else if researchError}
      <p class="err">{researchError}</p>
    {:else if research?.thesis}
      <p>{research.thesis.thesis}</p>
    {:else}
      <p class="muted">No cached research for this ticker.</p>
    {/if}
  </section>
</div>

<style>
  .panel {
    position: fixed;
    top: 0;
    right: 0;
    width: min(28rem, 100%);
    height: 100vh;
    overflow: auto;
    background: var(--paper);
    border-left: 1px solid var(--line);
    box-shadow: var(--shadow);
    padding: 1.25rem 1.35rem 2rem;
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
  }
  h2 {
    margin: 0;
    font-family: var(--font-display);
    font-size: 1.75rem;
  }
  .sub {
    margin: 0.25rem 0 0;
    color: var(--ink-soft);
    font-size: 0.85rem;
  }
  .close {
    border: 1px solid var(--line);
    background: white;
    border-radius: 2px;
    padding: 0.4rem 0.7rem;
    min-height: 40px;
  }
  h3 {
    margin: 1.1rem 0 0.4rem;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--ink-soft);
  }
  .action {
    font-weight: 500;
  }
  .ev {
    padding: 0.55rem 0;
    border-bottom: 1px solid var(--line);
  }
  .h {
    margin: 0;
    font-weight: 550;
  }
  .o,
  .meta,
  .explain,
  .muted {
    margin: 0.25rem 0 0;
    font-size: 0.88rem;
    color: var(--ink-soft);
  }
  .explain {
    color: var(--ink);
  }
  dl {
    margin: 0;
    display: grid;
    gap: 0.35rem;
  }
  dl div {
    display: grid;
    grid-template-columns: 7rem 1fr;
    gap: 0.5rem;
    font-size: 0.88rem;
  }
  dt {
    color: var(--ink-soft);
  }
  dd {
    margin: 0;
  }
  .err {
    color: var(--error);
  }
  @media (max-width: 720px) {
    .panel {
      width: 100%;
    }
  }
</style>
