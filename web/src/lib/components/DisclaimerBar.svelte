<script lang="ts">
  interface Props {
    text: string;
  }
  let { text }: Props = $props();
</script>

<aside class="disclaimer" role="note">
  {text}
</aside>

<style>
  .disclaimer {
    margin: 0;
    padding: 0.75rem 1.25rem;
    border-top: 1px solid var(--line);
    background: rgba(12, 27, 42, 0.04);
    color: var(--ink-soft);
    font-size: 0.8rem;
    line-height: 1.45;
  }
</style>
