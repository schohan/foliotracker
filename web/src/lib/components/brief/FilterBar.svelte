<script lang="ts">
  import type { BriefFilter } from "../../types";

  interface Props {
    active: BriefFilter;
    onchange: (f: BriefFilter) => void;
  }

  let { active, onchange }: Props = $props();

  const filters: { id: BriefFilter; label: string }[] = [
    { id: "all", label: "All" },
    { id: "high", label: "Critical" },
    { id: "positive", label: "Positive" },
    { id: "negative", label: "Negative" },
    { id: "earnings", label: "Earnings" },
    { id: "analyst", label: "Analyst" },
    { id: "products", label: "Products" },
    { id: "management", label: "Management" },
    { id: "sec", label: "SEC" },
    { id: "macro", label: "Macro" },
    { id: "held", label: "Held" },
    { id: "unread", label: "Unread" },
  ];
</script>

<div class="bar" role="toolbar" aria-label="Brief filters">
  {#each filters as f (f.id)}
    <button
      type="button"
      class:active={active === f.id}
      aria-pressed={active === f.id}
      onclick={() => onchange(f.id)}
    >
      {f.label}
    </button>
  {/each}
</div>

<style>
  .bar {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
    margin: 0 0 1rem;
  }
  button {
    border: 1px solid var(--line);
    background: white;
    color: var(--ink-soft);
    border-radius: 2px;
    padding: 0.35rem 0.65rem;
    min-height: 36px;
    font-size: 0.82rem;
  }
  button.active {
    border-color: var(--ink);
    background: var(--ink);
    color: var(--paper);
  }
</style>
