<script lang="ts">
  import type { DailyBrief } from "../../types";

  type Bucket = "today" | "yesterday" | "last_week" | "earlier";

  interface Props {
    history: DailyBrief[];
    activeGeneratedAt: string | null;
    onselect: (brief: DailyBrief) => void;
  }

  let { history, activeGeneratedAt, onselect }: Props = $props();

  function bucketFor(iso: string, now = new Date()): Bucket {
    const d = new Date(iso);
    const startToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const startYesterday = new Date(startToday);
    startYesterday.setDate(startYesterday.getDate() - 1);
    const startWeek = new Date(startToday);
    startWeek.setDate(startWeek.getDate() - 7);
    if (d >= startToday) return "today";
    if (d >= startYesterday) return "yesterday";
    if (d >= startWeek) return "last_week";
    return "earlier";
  }

  function label(b: Bucket): string {
    return (
      {
        today: "Today",
        yesterday: "Yesterday",
        last_week: "Last week",
        earlier: "Earlier",
      } as const
    )[b];
  }

  function shortWhen(iso: string): string {
    try {
      return new Date(iso).toLocaleString(undefined, {
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
      });
    } catch {
      return iso;
    }
  }

  const groups = $derived.by(() => {
    const order: Bucket[] = ["today", "yesterday", "last_week", "earlier"];
    const map: Record<Bucket, DailyBrief[]> = {
      today: [],
      yesterday: [],
      last_week: [],
      earlier: [],
    };
    for (const b of history) {
      map[bucketFor(b.generated_at)].push(b);
    }
    return order
      .filter((k) => map[k].length > 0)
      .map((k) => ({ bucket: k, items: map[k] }));
  });
</script>

<nav class="rail" aria-label="Brief timeline">
  <h2>Timeline</h2>
  {#if history.length === 0}
    <p class="muted">No history yet.</p>
  {:else}
    {#each groups as g (g.bucket)}
      <p class="bucket">{label(g.bucket)}</p>
      <ul>
        {#each g.items as brief (brief.generated_at)}
          <li>
            <button
              type="button"
              class:active={brief.generated_at === activeGeneratedAt}
              onclick={() => onselect(brief)}
            >
              <span class="when">{shortWhen(brief.generated_at)}</span>
              <span class="counts">
                {brief.summary?.high_count ?? 0}H /
                {brief.summary?.medium_count ?? brief.tickers.length}M
              </span>
            </button>
          </li>
        {/each}
      </ul>
    {/each}
  {/if}
</nav>

<style>
  .rail {
    margin: 0 0 1.25rem;
  }
  h2 {
    margin: 0 0 0.5rem;
    font-family: var(--font-display);
    font-size: 1.1rem;
  }
  .muted {
    color: var(--ink-soft);
    font-size: 0.88rem;
  }
  .bucket {
    margin: 0.65rem 0 0.25rem;
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--ink-soft);
    font-weight: 600;
  }
  ul {
    margin: 0;
    padding: 0;
    list-style: none;
  }
  button {
    display: flex;
    justify-content: space-between;
    gap: 0.75rem;
    width: 100%;
    text-align: left;
    border: 1px solid transparent;
    background: transparent;
    padding: 0.4rem 0.45rem;
    border-radius: 2px;
    min-height: 40px;
    color: var(--ink);
    font-size: 0.85rem;
  }
  button:hover {
    background: var(--accent-soft);
  }
  button.active {
    border-color: var(--line);
    background: rgba(255, 255, 255, 0.7);
  }
  .counts {
    color: var(--ink-soft);
    font-variant-numeric: tabular-nums;
  }
</style>
