<script lang="ts">
  interface Props {
    growth: number | null;
    value: number | null;
    risk: number | null;
  }
  let { growth, value, risk }: Props = $props();

  function fmt(n: number | null): string {
    return n == null ? "—" : Math.round(n).toString();
  }
</script>

<div class="scores" aria-label="Scorecard dimensions">
  <span><em>G</em> {fmt(growth)}</span>
  <span><em>V</em> {fmt(value)}</span>
  <span><em>R</em> {fmt(risk)}</span>
</div>

<style>
  .scores {
    display: flex;
    gap: 0.85rem;
    font-variant-numeric: tabular-nums;
    font-size: 0.9rem;
    color: var(--ink-soft);
  }
  em {
    font-style: normal;
    font-weight: 600;
    color: var(--ink);
    margin-right: 0.2rem;
  }
</style>
