<script lang="ts">
  import type { QuietTicker } from "../../types";
  import type { BriefEventItem } from "../../briefEvents";
  import EventRow from "./EventRow.svelte";

  interface Props {
    title: string;
    headingId: string;
    items?: BriefEventItem[];
    quiet?: QuietTicker[];
    expandedKey: string | null;
    focusKey: string | null;
    seen: Set<string>;
    ontoggle: (key: string) => void;
    onopen: (row: BriefEventItem["row"]) => void;
    onmark: (key: string) => void;
  }

  let {
    title,
    headingId,
    items = [],
    quiet = [],
    expandedKey,
    focusKey,
    seen,
    ontoggle,
    onopen,
    onmark,
  }: Props = $props();
</script>

<section class="section" aria-labelledby={headingId}>
  <h2 id={headingId}>{title}</h2>
  {#if quiet.length > 0}
    <ul class="quiet">
      {#each quiet as q (q.ticker)}
        <li>
          <span class="check" aria-hidden="true">✓</span>
          <span class="t">{q.ticker}</span>
          <span class="k">{q.list_kind}</span>
        </li>
      {/each}
    </ul>
  {:else if items.length === 0}
    <p class="empty">None in this section.</p>
  {:else}
    <div class="list">
      {#each items as item (`${item.row.ticker}-${item.bullet.event_key}`)}
        <EventRow
          row={item.row}
          bullet={item.bullet}
          expanded={expandedKey === item.bullet.event_key}
          focused={focusKey === item.bullet.event_key}
          unread={!seen.has(item.bullet.event_key)}
          ontoggle={() => ontoggle(item.bullet.event_key)}
          onopen={() => onopen(item.row)}
          onmark={() => onmark(item.bullet.event_key)}
        />
      {/each}
    </div>
  {/if}
</section>

<style>
  .section {
    margin: 0 0 1.75rem;
  }
  h2 {
    margin: 0 0 0.5rem;
    font-family: var(--font-display);
    font-size: 1.1rem;
    font-weight: 600;
  }
  .empty {
    color: var(--ink-soft);
    font-size: 0.9rem;
  }
  .quiet {
    display: flex;
    flex-wrap: wrap;
    gap: 0.45rem 1rem;
    margin: 0;
    padding: 0;
    list-style: none;
  }
  .quiet li {
    display: flex;
    align-items: baseline;
    gap: 0.35rem;
    font-size: 0.92rem;
  }
  .check {
    color: var(--ok);
  }
  .t {
    font-family: var(--font-display);
    font-weight: 600;
  }
  .k {
    font-size: 0.72rem;
    color: var(--ink-soft);
    text-transform: capitalize;
  }
</style>
