<script lang="ts">
  import type { BriefTicker, QuietTicker } from "../../types";

  interface Props {
    material: BriefTicker[];
    quiet: QuietTicker[];
    onselect: (ticker: string) => void;
  }

  let { material, quiet, onselect }: Props = $props();

  const cells = $derived.by(() => {
    const map = new Map<
      string,
      { ticker: string; list_kind: string; impact: number }
    >();
    for (const q of quiet) {
      map.set(q.ticker, { ticker: q.ticker, list_kind: q.list_kind, impact: 0 });
    }
    for (const t of material) {
      map.set(t.ticker, {
        ticker: t.ticker,
        list_kind: t.list_kind,
        impact: t.impact_score,
      });
    }
    return [...map.values()].sort((a, b) => {
      if (a.list_kind !== b.list_kind) return a.list_kind === "held" ? -1 : 1;
      return b.impact - a.impact || a.ticker.localeCompare(b.ticker);
    });
  });

  function sizeClass(list_kind: string): string {
    return list_kind === "held" ? "held" : "watched";
  }

  function impactClass(impact: number): string {
    if (impact >= 80) return "hot";
    if (impact >= 50) return "warm";
    return "calm";
  }
</script>

<section class="heat" aria-labelledby="heatmap-heading">
  <h2 id="heatmap-heading">Portfolio heat</h2>
  <p class="hint">Size = Held vs Watched · color = impact</p>
  <div class="grid">
    {#each cells as c (c.ticker)}
      <button
        type="button"
        class="cell {sizeClass(c.list_kind)} {impactClass(c.impact)}"
        title="{c.ticker} · impact {c.impact}"
        onclick={() => onselect(c.ticker)}
      >
        <span class="t">{c.ticker}</span>
        {#if c.impact > 0}
          <span class="i">{c.impact}</span>
        {/if}
      </button>
    {/each}
  </div>
</section>

<style>
  .heat {
    margin: 0 0 1.75rem;
  }
  h2 {
    margin: 0;
    font-family: var(--font-display);
    font-size: 1.1rem;
  }
  .hint {
    margin: 0.25rem 0 0.65rem;
    font-size: 0.8rem;
    color: var(--ink-soft);
  }
  .grid {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
  }
  .cell {
    border: 1px solid var(--line);
    border-radius: 2px;
    background: rgba(255, 255, 255, 0.65);
    color: var(--ink);
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    justify-content: center;
    padding: 0.35rem 0.5rem;
    min-height: 40px;
  }
  .cell.held {
    min-width: 4.5rem;
    font-size: 0.95rem;
  }
  .cell.watched {
    min-width: 3.4rem;
    font-size: 0.82rem;
    opacity: 0.85;
  }
  .cell.hot {
    border-color: var(--error);
    background: rgba(163, 32, 32, 0.08);
  }
  .cell.warm {
    border-color: var(--accent);
    background: var(--accent-soft);
  }
  .cell.calm {
    border-color: var(--line);
  }
  .t {
    font-family: var(--font-display);
    font-weight: 600;
  }
  .i {
    font-size: 0.7rem;
    color: var(--ink-soft);
  }
</style>
