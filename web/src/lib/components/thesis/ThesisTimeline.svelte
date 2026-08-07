<script lang="ts">
  import { formatThesisVerdict } from "../../thesisFormat";
  import type { ThesisMonitoring } from "../../types";

  interface Props {
    monitoring: ThesisMonitoring;
  }

  let { monitoring }: Props = $props();

  function formatAsOf(iso: string): string {
    const d = new Date(iso);
    return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString();
  }
</script>

<article class="panel" aria-label="Thesis timeline">
  <header>
    <h3>Thesis monitoring</h3>
  </header>

  <section class="original" aria-labelledby="original-heading">
    <h4 id="original-heading">Original thesis</h4>
    <p class="thesis-text">{monitoring.original_thesis || "—"}</p>
  </section>

  {#if monitoring.current}
    <section class="current" aria-labelledby="current-heading">
      <h4 id="current-heading">Current assessment</h4>
      <p
        class="verdict verdict-{monitoring.current.verdict}"
      >
        {formatThesisVerdict(monitoring.current.verdict)}
      </p>
      {#if monitoring.current.narrative}
        <p class="narrative">{monitoring.current.narrative}</p>
      {/if}
      <p class="meta">
        Provider: {monitoring.current.insight_mode}
        · {formatAsOf(monitoring.current.as_of)}
      </p>
      {#if monitoring.current.evidence.length > 0}
        <ul class="evidence">
          {#each monitoring.current.evidence as line (line)}
            <li>{line}</li>
          {/each}
        </ul>
      {/if}
    </section>
  {/if}

  {#if monitoring.timeline.length > 0}
    <section class="timeline" aria-labelledby="timeline-heading">
      <h4 id="timeline-heading">Timeline</h4>
      <ol class="events">
        {#each monitoring.timeline as event, i (event.as_of + String(i))}
          <li>
            <span class="when">{formatAsOf(event.as_of)}</span>
            <span class="verdict-chip verdict-{event.verdict}">
              {formatThesisVerdict(event.verdict)}
            </span>
            {#if event.narrative}
              <p class="event-narr">{event.narrative}</p>
            {/if}
          </li>
        {/each}
      </ol>
    </section>
  {/if}
</article>

<style>
  .panel {
    border: 1px solid var(--line);
    border-radius: 3px;
    padding: 1rem 1.1rem;
  }
  header {
    margin-bottom: 0.75rem;
  }
  h3 {
    margin: 0;
    font-family: var(--font-display);
    font-size: 1.1rem;
    font-weight: 600;
  }
  h4 {
    margin: 0 0 0.4rem;
    font-size: 0.75rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--ink-soft);
  }
  .original,
  .current,
  .timeline {
    margin-bottom: 1rem;
  }
  .thesis-text {
    margin: 0;
    white-space: pre-wrap;
    line-height: 1.45;
  }
  .verdict {
    margin: 0 0 0.4rem;
    font-family: var(--font-display);
    font-size: 1.25rem;
    font-weight: 700;
  }
  .verdict-no_change {
    color: var(--ink-soft);
  }
  .verdict-strengthened {
    color: var(--ok);
  }
  .verdict-slightly_weaker {
    color: var(--partial);
  }
  .verdict-broken {
    color: var(--error);
  }
  .narrative {
    margin: 0 0 0.4rem;
    line-height: 1.45;
  }
  .meta {
    margin: 0 0 0.5rem;
    color: var(--ink-soft);
    font-size: 0.85rem;
  }
  .evidence {
    margin: 0;
    padding-left: 1.1rem;
    color: var(--ink-soft);
    font-size: 0.9rem;
    line-height: 1.4;
  }
  .events {
    margin: 0;
    padding: 0;
    list-style: none;
  }
  .events > li {
    display: grid;
    grid-template-columns: 6.5rem 1fr;
    gap: 0.35rem 0.75rem;
    padding: 0.55rem 0;
    border-bottom: 1px solid var(--line);
    font-size: 0.9rem;
  }
  .when {
    color: var(--ink-soft);
  }
  .verdict-chip {
    font-weight: 600;
  }
  .event-narr {
    grid-column: 1 / -1;
    margin: 0;
    color: var(--ink-soft);
    font-size: 0.85rem;
    line-height: 1.4;
  }
</style>
