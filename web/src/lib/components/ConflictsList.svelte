<script lang="ts">
  import type { EvidenceConflict } from "../types";

  interface Props {
    conflicts: EvidenceConflict[];
  }
  let { conflicts }: Props = $props();
</script>

{#if conflicts.length === 0}
  <p class="empty">No source conflicts.</p>
{:else}
  <ul>
    {#each conflicts as c (c.id)}
      <li>
        <strong>{c.topic}</strong>
        <span class="sev">{c.severity}</span>
        <p>{c.summary}</p>
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
    gap: 0.75rem;
  }
  li {
    border-left: 3px solid var(--accent);
    padding-left: 0.75rem;
  }
  .sev {
    margin-left: 0.5rem;
    font-size: 0.7rem;
    text-transform: uppercase;
    color: var(--ink-soft);
  }
  p {
    margin: 0.25rem 0 0;
    color: var(--ink-soft);
    line-height: 1.4;
    font-size: 0.9rem;
  }
  .empty {
    color: var(--ink-soft);
    font-size: 0.9rem;
  }
</style>
