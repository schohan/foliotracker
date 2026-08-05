<script lang="ts">
  import type { BriefSource } from "../../types";

  interface Props {
    sources: BriefSource[];
  }

  let { sources }: Props = $props();
</script>

{#if sources.length > 0}
  <ul class="sources">
    {#each sources as s, i (`${s.label}-${i}`)}
      <li>
        {#if s.url}
          <a href={s.url} target="_blank" rel="noreferrer">{s.label}</a>
        {:else}
          <span>{s.label}</span>
        {/if}
      </li>
    {/each}
  </ul>
{/if}

<style>
  .sources {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem 0.75rem;
    margin: 0.35rem 0 0;
    padding: 0;
    list-style: none;
    font-size: 0.82rem;
  }
  .sources a {
    color: var(--accent);
    text-decoration: underline;
    text-underline-offset: 2px;
  }
  .sources span {
    color: var(--ink-soft);
  }
</style>
