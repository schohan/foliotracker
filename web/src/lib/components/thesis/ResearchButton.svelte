<script lang="ts">
  import { explainThesis } from "../../api";
  import type { ThesisExplainAnswer } from "../../types";

  interface Props {
    ticker: string;
  }

  let { ticker }: Props = $props();

  const QUESTIONS: { id: string; label: string }[] = [
    {
      id: "framework_disagree",
      label: "Why Graham vs Financial Strength?",
    },
    {
      id: "mos_change",
      label: "Why did Margin of Safety move?",
    },
    {
      id: "most_bullish",
      label: "Which framework is most bullish?",
    },
  ];

  let busyId = $state<string | null>(null);
  let error = $state<string | null>(null);
  let answer = $state<ThesisExplainAnswer | null>(null);

  async function ask(questionId: string) {
    if (busyId != null) return;
    busyId = questionId;
    error = null;
    try {
      answer = await explainThesis({ ticker, question_id: questionId });
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
      answer = null;
    } finally {
      busyId = null;
    }
  }
</script>

<article class="panel" aria-label="AI Research">
  <header>
    <h3>AI Research</h3>
    <p class="hint">One-click framework questions — provider-labeled, fail-closed.</p>
  </header>

  <div class="actions" role="group" aria-label="Research questions">
    {#each QUESTIONS as q (q.id)}
      <button
        type="button"
        class="ask"
        disabled={busyId != null}
        onclick={() => void ask(q.id)}
      >
        {busyId === q.id ? "Asking…" : q.label}
      </button>
    {/each}
  </div>

  {#if error}
    <p class="error" role="alert">{error}</p>
  {/if}

  {#if answer}
    <section class="result" aria-live="polite">
      <p class="q">{answer.question}</p>
      <p class="a">{answer.answer}</p>
      <p class="meta">Provider: {answer.provider}</p>
      {#if answer.evidence.length > 0}
        <ul class="evidence">
          {#each answer.evidence as line (line)}
            <li>{line}</li>
          {/each}
        </ul>
      {/if}
    </section>
  {/if}
</article>

<style>
  .panel {
    border: 1px solid var(--line);
    border-radius: 3px;
    padding: 1rem 1.1rem;
  }
  header {
    margin-bottom: 0.75rem;
  }
  h3 {
    margin: 0 0 0.35rem;
    font-family: var(--font-display);
    font-size: 1.1rem;
    font-weight: 600;
  }
  .hint {
    margin: 0;
    color: var(--ink-soft);
    font-size: 0.85rem;
  }
  .actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
  }
  .ask {
    border: 1px solid var(--ink);
    background: transparent;
    color: var(--ink);
    padding: 0.45rem 0.75rem;
    min-height: 44px;
    border-radius: 2px;
    font-weight: 500;
    font-size: 0.85rem;
  }
  .ask:disabled {
    opacity: 0.6;
  }
  .error {
    margin: 0.75rem 0 0;
    color: var(--error);
    font-size: 0.9rem;
  }
  .result {
    margin-top: 0.9rem;
    padding-top: 0.75rem;
    border-top: 1px solid var(--line);
  }
  .q {
    margin: 0 0 0.4rem;
    font-weight: 600;
    font-size: 0.9rem;
  }
  .a {
    margin: 0 0 0.4rem;
    line-height: 1.45;
  }
  .meta {
    margin: 0 0 0.4rem;
    color: var(--ink-soft);
    font-size: 0.85rem;
  }
  .evidence {
    margin: 0;
    padding-left: 1.1rem;
    color: var(--ink-soft);
    font-size: 0.85rem;
    line-height: 1.4;
  }
</style>
