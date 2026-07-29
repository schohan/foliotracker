<script lang="ts">
  import type { EvidenceConflict } from "../types";

  interface Props {
    conflicts: EvidenceConflict[];
  }
  let { conflicts }: Props = $props();
</script>

{#if conflicts.length === 0}
  <p class="empty">No source conflicts detected.</p>
{:else}
  <ul>
    {#each conflicts as c (c.id)}
      <li>
        <div class="head">
          <strong class="topic">{c.topic}</strong>
          <span class="sev">{c.severity}</span>
        </div>
        <p class="summary">{c.summary}</p>
      </li>
    {/each}
  </ul>
{/if}

<style>
  ul {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: 0.85rem;
  }
  li {
    padding: 0;
  }
  .head {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 0.4rem 0.65rem;
  }
  .topic {
    font-weight: 600;
    color: var(--ink);
  }
  .sev {
    font-size: 0.68rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--ink-soft);
  }
  .summary {
    margin: 0.3rem 0 0;
    color: var(--ink-soft);
    line-height: 1.4;
    font-size: 0.9rem;
  }
  .empty {
    color: var(--ink-soft);
    font-size: 0.9rem;
    margin: 0;
  }
</style>
