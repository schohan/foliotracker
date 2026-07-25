<script lang="ts">
  import type { Phase0Result } from "../types";
  import ConflictsList from "./ConflictsList.svelte";

  interface Props {
    result: Phase0Result | null;
    loading?: boolean;
    error?: string | null;
    onclose: () => void;
  }
  let { result, loading = false, error = null, onclose }: Props = $props();

  function scoreLabel(n: number | null | undefined): string {
    return n == null ? "—" : Math.round(n).toString();
  }
</script>

<aside class="panel" aria-label="Ticker detail">
  <header>
    <h2>{result?.ticker ?? "Detail"}</h2>
    <button type="button" onclick={onclose} aria-label="Close">Close</button>
  </header>

  {#if loading}
    <p class="muted">Loading research…</p>
  {:else if error}
    <p class="err">{error}</p>
  {:else if result}
    <p class={`badge ${result.status}`}>{result.status}</p>
    {#if result.error_message}
      <p class="err">{result.error_message}</p>
    {/if}

    <section>
      <h3>Scorecard</h3>
      {#if result.scorecard}
        <dl class="grid">
          <div><dt>Growth</dt><dd>{scoreLabel(result.scorecard.growth_score)}</dd></div>
          <div><dt>Value</dt><dd>{scoreLabel(result.scorecard.value_score)}</dd></div>
          <div><dt>Profitability</dt><dd>{scoreLabel(result.scorecard.profitability_score)}</dd></div>
          <div><dt>Moat</dt><dd>{scoreLabel(result.scorecard.moat_score)}</dd></div>
          <div><dt>Risk</dt><dd>{scoreLabel(result.scorecard.risk_score)}</dd></div>
          <div><dt>Execution</dt><dd>{scoreLabel(result.scorecard.execution_score)}</dd></div>
        </dl>
      {:else}
        <p class="muted">No scorecard.</p>
      {/if}
    </section>

    <section>
      <h3>Thesis</h3>
      {#if result.thesis}
        <p class="thesis">{result.thesis.thesis}</p>
        <ul class="claims">
          {#each result.thesis.claims as claim}
            <li>
              {claim.text}
              <span class="ids">{claim.evidence_ids.join(", ")}</span>
            </li>
          {/each}
        </ul>
      {:else}
        <p class="muted">No thesis.</p>
      {/if}
    </section>

    <section>
      <h3>Conflicts</h3>
      <ConflictsList conflicts={result.evidence?.conflicts ?? []} />
    </section>

    <section>
      <h3>Fundamentals</h3>
      {#if result.fundamentals}
        <dl class="grid">
          <div><dt>Forward P/E</dt><dd>{result.fundamentals.forward_pe ?? "—"}</dd></div>
          <div><dt>Trailing P/E</dt><dd>{result.fundamentals.pe_ratio ?? result.fundamentals.trailing_pe ?? "—"}</dd></div>
          <div><dt>EPS trailing</dt><dd>{result.fundamentals.eps_trailing ?? "—"}</dd></div>
          <div><dt>Source</dt><dd>{result.fundamentals.source_id ?? "—"}</dd></div>
        </dl>
      {:else}
        <p class="muted">No fundamentals.</p>
      {/if}
    </section>

    <details>
      <summary>Raw JSON</summary>
      <pre>{JSON.stringify(result, null, 2)}</pre>
    </details>

    <p class="meta">request_id {result.request_id} · cache_hit {String(result.cache_hit)}</p>
  {/if}
</aside>

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
  header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
    margin-bottom: 1rem;
  }
  h2 {
    margin: 0;
    font-family: var(--font-display);
    font-size: 1.75rem;
  }
  h3 {
    margin: 1.25rem 0 0.5rem;
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--ink-soft);
  }
  header button {
    border: 1px solid var(--line);
    background: white;
    padding: 0.4rem 0.7rem;
    border-radius: 2px;
  }
  .badge {
    display: inline-block;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
  }
  .badge.ok {
    color: var(--ok);
  }
  .badge.partial {
    color: var(--partial);
  }
  .badge.error {
    color: var(--error);
  }
  .grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.5rem 1rem;
    margin: 0;
  }
  dt {
    font-size: 0.75rem;
    color: var(--ink-soft);
  }
  dd {
    margin: 0;
    font-variant-numeric: tabular-nums;
    font-weight: 500;
  }
  .thesis {
    line-height: 1.45;
  }
  .claims {
    padding-left: 1.1rem;
    color: var(--ink-soft);
  }
  .ids {
    display: block;
    font-size: 0.75rem;
    color: var(--accent);
  }
  .muted {
    color: var(--ink-soft);
  }
  .err {
    color: var(--error);
  }
  .meta {
    margin-top: 1.5rem;
    font-size: 0.75rem;
    color: var(--ink-soft);
  }
  pre {
    overflow: auto;
    font-size: 0.7rem;
    background: rgba(12, 27, 42, 0.04);
    padding: 0.75rem;
    max-height: 16rem;
  }
  @keyframes slide {
    from {
      transform: translateX(16px);
      opacity: 0;
    }
    to {
      transform: none;
      opacity: 1;
    }
  }
</style>
