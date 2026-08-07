<script lang="ts">
  import { onMount } from "svelte";
  import type { ThesisHelpEntry } from "../../thesisHelp";

  interface Props {
    entry: ThesisHelpEntry;
    /** Optional compact placement hint for CSS. */
    align?: "start" | "end";
  }

  let { entry, align = "start" }: Props = $props();

  let open = $state(false);
  let rootEl: HTMLElement | undefined = $state();
  let btnEl: HTMLButtonElement | undefined = $state();

  function toggle(e: MouseEvent) {
    e.stopPropagation();
    e.preventDefault();
    open = !open;
  }

  function onDocPointer(e: PointerEvent) {
    if (!open || !rootEl) return;
    if (e.target instanceof Node && rootEl.contains(e.target)) return;
    open = false;
  }

  function onKey(e: KeyboardEvent) {
    if (e.key === "Escape" && open) {
      e.preventDefault();
      e.stopImmediatePropagation();
      open = false;
      btnEl?.focus();
    }
  }

  onMount(() => {
    document.addEventListener("pointerdown", onDocPointer);
    window.addEventListener("keydown", onKey, true);
    return () => {
      document.removeEventListener("pointerdown", onDocPointer);
      window.removeEventListener("keydown", onKey, true);
    };
  });
</script>

<span class="help" class:open bind:this={rootEl} data-align={align}>
  <button
    type="button"
    class="icon"
    bind:this={btnEl}
    aria-expanded={open}
    aria-label={`Help: ${entry.title}`}
    onclick={toggle}
  >
    ?
  </button>
  {#if open}
    <div class="tip" role="dialog" aria-label={entry.title}>
      <p class="title">{entry.title}</p>
      <dl>
        <div>
          <dt>What</dt>
          <dd>{entry.what}</dd>
        </div>
        <div>
          <dt>How</dt>
          <dd>{entry.how}</dd>
        </div>
        <div>
          <dt>Why it matters</dt>
          <dd>{entry.why}</dd>
        </div>
      </dl>
    </div>
  {/if}
</span>

<style>
  .help {
    position: relative;
    display: inline-flex;
    vertical-align: middle;
    margin-left: 0.2rem;
  }
  .icon {
    width: 1.15rem;
    height: 1.15rem;
    min-width: 1.15rem;
    min-height: 1.15rem;
    padding: 0;
    border-radius: 50%;
    border: 1px solid var(--line);
    background: var(--paper-deep, var(--paper));
    color: var(--ink-soft);
    font-size: 0.68rem;
    font-weight: 700;
    line-height: 1;
    cursor: help;
  }
  .icon:hover,
  .icon:focus-visible,
  .help.open .icon {
    color: var(--accent);
    border-color: var(--accent);
    outline: none;
  }
  .icon:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 1px;
  }
  .tip {
    position: absolute;
    z-index: 40;
    top: calc(100% + 0.35rem);
    left: 0;
    width: min(18.5rem, 70vw);
    padding: 0.7rem 0.8rem;
    background: var(--paper);
    border: 1px solid var(--line);
    border-radius: 2px;
    box-shadow: var(--shadow, 0 8px 24px rgba(12, 27, 42, 0.12));
    text-align: left;
    text-transform: none;
    letter-spacing: normal;
    font-family: var(--font-body);
    font-weight: 400;
    white-space: normal;
  }
  .help[data-align="end"] .tip {
    left: auto;
    right: 0;
  }
  .title {
    margin: 0 0 0.45rem;
    font-family: var(--font-display);
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--ink);
  }
  dl {
    margin: 0;
    display: grid;
    gap: 0.4rem;
  }
  dl div {
    display: grid;
    gap: 0.1rem;
  }
  dt {
    font-size: 0.68rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--ink-soft);
  }
  dd {
    margin: 0;
    font-size: 0.8rem;
    line-height: 1.4;
    color: var(--ink);
  }
</style>
