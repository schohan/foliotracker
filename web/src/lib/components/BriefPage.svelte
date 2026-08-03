<script lang="ts">
  import { onMount } from "svelte";
  import { fetchBrief, generateBrief, logBriefMiss } from "../api";
  import type { AppView, DailyBrief } from "../types";
  import DisclaimerBar from "./DisclaimerBar.svelte";
  import PrimaryNav from "./PrimaryNav.svelte";

  interface Props {
    view: AppView;
    onnavigate: (view: AppView) => void;
  }

  let { view, onnavigate }: Props = $props();

  let brief = $state<DailyBrief | null>(null);
  let loadError = $state<string | null>(null);
  let loading = $state(true);
  let generating = $state(false);
  let forceRefresh = $state(false);
  let missNote = $state("");
  let missBusy = $state(false);
  let missSaved = $state(false);

  const emptyUniverse = $derived(
    brief != null &&
      brief.universe_count === 0 &&
      (brief.empty_message?.toLowerCase().includes("add tickers") ?? false),
  );
  const nothingMaterial = $derived(
    brief != null &&
      brief.universe_count > 0 &&
      brief.tickers.length === 0 &&
      brief.empty_message != null,
  );

  function formatPct(v: number | null | undefined): string {
    if (v == null || Number.isNaN(v)) return "—";
    const pct = v * 100;
    const sign = pct > 0 ? "+" : "";
    return `${sign}${pct.toFixed(1)}%`;
  }

  function formatScore(v: number | null | undefined): string {
    if (v == null || Number.isNaN(v)) return "—";
    return v.toFixed(0);
  }

  function formatWhen(iso: string): string {
    try {
      return new Date(iso).toLocaleString(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
      });
    } catch {
      return iso;
    }
  }

  async function load() {
    loading = true;
    loadError = null;
    try {
      brief = await fetchBrief();
    } catch (e) {
      loadError = e instanceof Error ? e.message : String(e);
    } finally {
      loading = false;
    }
  }

  async function onGenerate() {
    if (generating) return;
    generating = true;
    loadError = null;
    try {
      brief = await generateBrief(forceRefresh);
    } catch (e) {
      loadError = e instanceof Error ? e.message : String(e);
    } finally {
      generating = false;
    }
  }

  async function onMissSubmit(e: Event) {
    e.preventDefault();
    const note = missNote.trim();
    if (!note || missBusy) return;
    missBusy = true;
    missSaved = false;
    try {
      await logBriefMiss(note);
      missNote = "";
      missSaved = true;
    } catch (err) {
      loadError = err instanceof Error ? err.message : String(err);
    } finally {
      missBusy = false;
    }
  }

  onMount(() => {
    void load();
  });

  const defaultDisclaimer =
    "FolioTracker output is for informational and educational purposes only. It is not investment, legal, or tax advice. Do your own research.";
</script>

<main class="page">
  <header class="hero">
    <p class="brand">FolioTracker</p>
    <PrimaryNav {view} {onnavigate} />
    <p class="tag">
      Daily Decision Brief — material events across Held and Watched. Informs
      trim / add / promote. Not advice.
    </p>
  </header>

  <div class="toolbar">
    <button
      type="button"
      class="generate"
      disabled={generating}
      onclick={() => void onGenerate()}
    >
      {generating ? "Generating…" : "Generate today"}
    </button>
    <label class="force">
      <input type="checkbox" bind:checked={forceRefresh} disabled={generating} />
      Force refresh
    </label>
  </div>

  {#if generating}
    <p class="muted" aria-live="polite">Generating today’s brief…</p>
  {/if}

  {#if loadError}
    <div class="banner" role="alert">
      <p>{loadError}</p>
      <button type="button" class="retry" onclick={() => void onGenerate()}>
        Retry Generate
      </button>
    </div>
  {/if}

  {#if brief && (brief.generation_status === "partial" || brief.generation_status === "stale")}
    <div class="banner soft" role="status">
      <p>
        Generation {brief.generation_status}
        {#if brief.gaps.length > 0}
          — some sources or tickers incomplete.
        {/if}
      </p>
    </div>
  {/if}

  {#if loading && !brief}
    <p class="muted">Loading brief…</p>
  {:else if !brief}
    <p class="empty">
      No brief yet. Add tickers on Watchlist, then Generate today.
    </p>
    <button type="button" class="goto" onclick={() => onnavigate("watchlist")}>
      Go to Watchlist
    </button>
  {:else if emptyUniverse}
    <p class="empty">{brief.empty_message}</p>
    <button type="button" class="goto" onclick={() => onnavigate("watchlist")}>
      Go to Watchlist
    </button>
  {:else}
    <div class="meta" aria-live="polite">
      <p>
        <span class="status status-{brief.generation_status}"
          >{brief.generation_status}</span
        >
        · {formatWhen(brief.generated_at)}
        · universe {brief.universe_count}
        · considered {brief.tickers_considered}
        · surfaced {brief.tickers.length}
      </p>
    </div>

    {#if nothingMaterial}
      <p class="empty calm">{brief.empty_message}</p>
    {:else}
      <section class="block" aria-labelledby="brief-heading">
        <h2 id="brief-heading">Material today</h2>
        <table>
          <thead>
            <tr>
              <th scope="col">Ticker</th>
              <th scope="col">List</th>
              <th scope="col">Daily</th>
              <th scope="col">Metrics</th>
              <th scope="col">Bullets</th>
            </tr>
          </thead>
          <tbody>
            {#each brief.tickers as row (row.ticker)}
              <tr class="row status-{row.status}">
                <th scope="row">{row.ticker}</th>
                <td class="list">{row.list_kind}</td>
                <td class="ret">{formatPct(row.daily_return)}</td>
                <td class="metrics">
                  P/E {formatScore(row.trailing_pe)} · 1Y {formatPct(row.return_1y)}
                  · G {formatScore(row.growth_score)} / V {formatScore(row.value_score)}
                  / R {formatScore(row.risk_score)}
                </td>
                <td>
                  {#if row.status === "unavailable"}
                    <span class="muted">Unavailable</span>
                  {:else if row.bullets.length === 0}
                    <span class="muted">Move only</span>
                  {:else}
                    <ul class="bullets">
                      {#each row.bullets as b, i (`${row.ticker}-${i}`)}
                        <li>
                          <span class="cat">{b.category}</span>
                          {#if b.source_url}
                            <a href={b.source_url} target="_blank" rel="noreferrer"
                              >{b.text}</a
                            >
                          {:else}
                            {b.text}
                          {/if}
                        </li>
                      {/each}
                    </ul>
                  {/if}
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </section>
    {/if}

    {#if brief.gaps.length > 0}
      <ul class="gaps">
        {#each brief.gaps as gap (gap)}
          <li>{gap}</li>
        {/each}
      </ul>
    {/if}

    <section class="miss" aria-labelledby="miss-heading">
      <h2 id="miss-heading">Miss log</h2>
      <p class="muted">
        Note a material miss you noticed (dogfood). Append-only; not shown in
        the Brief ranking.
      </p>
      <form class="miss-form" onsubmit={onMissSubmit}>
        <label class="sr">
          Miss note
          <input
            bind:value={missNote}
            maxlength={2000}
            placeholder="Material miss I noticed…"
            disabled={missBusy}
          />
        </label>
        <button type="submit" disabled={missBusy || !missNote.trim()}>
          {missBusy ? "Saving…" : "Log miss"}
        </button>
      </form>
      {#if missSaved}
        <p class="muted" aria-live="polite">Saved.</p>
      {/if}
    </section>
  {/if}

  <DisclaimerBar text={brief?.disclaimer ?? defaultDisclaimer} />
</main>

<style>
  .page {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    padding: 1.5rem 1.25rem 0;
    max-width: 72rem;
    margin: 0 auto;
  }
  .hero {
    margin-bottom: 0.75rem;
  }
  .brand {
    margin: 0;
    font-family: var(--font-display);
    font-size: clamp(1.75rem, 4vw, 2.35rem);
    font-weight: 600;
    letter-spacing: -0.02em;
    color: var(--ink);
  }
  .tag {
    margin: 0.65rem 0 0;
    color: var(--ink-soft);
    max-width: 40rem;
    line-height: 1.45;
  }
  .toolbar {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
    align-items: center;
    margin: 0.5rem 0 1rem;
  }
  .generate {
    border: 1px solid var(--ink);
    background: var(--ink);
    color: var(--paper);
    border-radius: 2px;
    padding: 0.55rem 0.9rem;
    min-height: 44px;
    font-weight: 500;
  }
  .generate:disabled {
    opacity: 0.55;
    cursor: not-allowed;
  }
  .force {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    color: var(--ink-soft);
    font-size: 0.9rem;
    min-height: 44px;
  }
  .banner {
    border: 1px solid var(--line);
    background: rgba(176, 74, 46, 0.08);
    padding: 0.75rem 1rem;
    margin-bottom: 1rem;
    border-radius: 2px;
  }
  .banner.soft {
    background: rgba(12, 27, 42, 0.04);
  }
  .banner p {
    margin: 0 0 0.5rem;
  }
  .retry,
  .goto {
    border: 1px solid var(--line);
    background: white;
    color: var(--ink);
    border-radius: 2px;
    padding: 0.45rem 0.75rem;
    min-height: 44px;
  }
  .muted {
    color: var(--ink-soft);
    font-size: 0.9rem;
  }
  .empty {
    margin: 1.5rem 0 1rem;
    color: var(--ink-soft);
    max-width: 28rem;
    line-height: 1.5;
  }
  .empty.calm {
    font-size: 1.05rem;
    color: var(--ink);
  }
  .meta {
    margin: 0 0 1rem;
    font-size: 0.9rem;
    color: var(--ink-soft);
  }
  .status {
    text-transform: uppercase;
    letter-spacing: 0.04em;
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--ink);
  }
  .block {
    margin-bottom: 1.5rem;
  }
  h2 {
    margin: 0 0 0.65rem;
    font-family: var(--font-display);
    font-size: 1.15rem;
    font-weight: 600;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.92rem;
  }
  th,
  td {
    text-align: left;
    padding: 0.65rem 0.5rem;
    border-bottom: 1px solid var(--line);
    vertical-align: top;
  }
  thead th {
    color: var(--ink-soft);
    font-weight: 500;
    font-size: 0.8rem;
  }
  .list {
    text-transform: capitalize;
  }
  .ret {
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }
  .metrics {
    color: var(--ink-soft);
    font-size: 0.82rem;
    white-space: nowrap;
  }
  .bullets {
    margin: 0;
    padding-left: 1.1rem;
  }
  .bullets li {
    margin: 0.2rem 0;
  }
  .cat {
    display: inline-block;
    margin-right: 0.35rem;
    color: var(--ink-soft);
    font-size: 0.75rem;
  }
  .gaps {
    margin: 0 0 1.25rem;
    padding-left: 1.1rem;
    color: var(--ink-soft);
    font-size: 0.85rem;
  }
  .miss {
    margin: 0 0 2rem;
  }
  .miss-form {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin-top: 0.5rem;
  }
  .sr {
    display: contents;
  }
  .miss-form input {
    min-width: min(28rem, 100%);
    border: 1px solid var(--line);
    border-radius: 2px;
    padding: 0.55rem 0.75rem;
    min-height: 44px;
    background: white;
    color: var(--ink);
  }
  .miss-form button {
    border: 1px solid var(--line);
    background: white;
    color: var(--ink);
    border-radius: 2px;
    padding: 0.55rem 0.75rem;
    min-height: 44px;
  }
  .miss-form button:disabled {
    opacity: 0.5;
  }
  @media (max-width: 720px) {
    .metrics {
      white-space: normal;
    }
    table,
    thead,
    tbody,
    th,
    td,
    tr {
      display: block;
    }
    thead {
      position: absolute;
      width: 1px;
      height: 1px;
      overflow: hidden;
      clip: rect(0 0 0 0);
    }
    tr {
      border-bottom: 1px solid var(--line);
      padding: 0.75rem 0;
    }
    th,
    td {
      border: none;
      padding: 0.2rem 0;
    }
  }
</style>
