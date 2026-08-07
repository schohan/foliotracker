<script lang="ts">
  import { onMount } from "svelte";
  import {
    fetchBrief,
    fetchBriefHistory,
    fetchResearch,
    generateBrief,
    logBriefMiss,
  } from "../api";
  import { loadSeenKeys, markSeen } from "../briefUnread";
  import type {
    AppView,
    BriefFilter,
    BriefTicker,
    DailyBrief,
    Phase0Result,
  } from "../types";
  import type { BriefEventItem } from "../briefEvents";
  import DisclaimerBar from "./DisclaimerBar.svelte";
  import PrimaryNav from "./PrimaryNav.svelte";
  import FilterBar from "./brief/FilterBar.svelte";
  import HeatMap from "./brief/HeatMap.svelte";
  import PortfolioSummary from "./brief/PortfolioSummary.svelte";
  import MorningCounts from "./brief/MorningCounts.svelte";
  import PrioritySection from "./brief/PrioritySection.svelte";
  import StockDrawer from "./brief/StockDrawer.svelte";
  import TimelineRail from "./brief/TimelineRail.svelte";

  interface Props {
    view: AppView;
    onnavigate: (view: AppView) => void;
  }

  let { view, onnavigate }: Props = $props();

  let brief = $state<DailyBrief | null>(null);
  let history = $state<DailyBrief[]>([]);
  let loadError = $state<string | null>(null);
  let loading = $state(true);
  let generating = $state(false);
  let forceRefresh = $state(false);
  let missNote = $state("");
  let missBusy = $state(false);
  let missSaved = $state(false);
  let filter = $state<BriefFilter>("all");
  let expandedKey = $state<string | null>(null);
  let focusKey = $state<string | null>(null);
  let seen = $state<Set<string>>(new Set());
  let drawerRow = $state<BriefTicker | null>(null);
  let research = $state<Phase0Result | null>(null);
  let researchLoading = $state(false);
  let researchError = $state<string | null>(null);

  const emptyUniverse = $derived(
    brief != null &&
      brief.universe_count === 0 &&
      (brief.empty_message?.toLowerCase().includes("add tickers") ?? false),
  );

  const allEvents = $derived.by((): BriefEventItem[] => {
    if (!brief) return [];
    const out: BriefEventItem[] = [];
    for (const row of brief.tickers) {
      for (const bullet of row.bullets) {
        out.push({ row, bullet });
      }
    }
    return out.sort(
      (a, b) =>
        b.bullet.impact_score - a.bullet.impact_score ||
        a.row.ticker.localeCompare(b.row.ticker),
    );
  });

  function matchesFilter(
    item: BriefEventItem,
    f: BriefFilter,
    seenKeys: Set<string>,
  ): boolean {
    const { row, bullet } = item;
    const cat = bullet.category;
    switch (f) {
      case "all":
        return true;
      case "high":
        return bullet.priority === "high";
      case "positive":
        return bullet.sentiment === "positive";
      case "negative":
        return bullet.sentiment === "negative";
      case "earnings":
        return cat === "earnings_guidance";
      case "analyst":
        return cat === "analyst_rating";
      case "products":
        return cat === "product_announcement";
      case "management":
        return /ceo|cfo|resign|management|executive/i.test(bullet.text);
      case "sec":
        return cat === "regulatory_material";
      case "macro":
        return cat === "other_material" || cat === "price_move";
      case "held":
        return row.list_kind === "held";
      case "unread":
        return !seenKeys.has(bullet.event_key);
      default:
        return true;
    }
  }

  const filteredEvents = $derived(
    allEvents.filter((e) => matchesFilter(e, filter, seen)),
  );

  const highItems = $derived(
    filteredEvents.filter((e) => e.bullet.priority === "high"),
  );
  const mediumItems = $derived(
    filteredEvents.filter((e) => e.bullet.priority === "medium"),
  );

  const focusKeys = $derived(filteredEvents.map((e) => e.bullet.event_key));

  async function loadHistory() {
    try {
      history = await fetchBriefHistory();
    } catch {
      history = [];
    }
  }

  async function load() {
    loading = true;
    loadError = null;
    try {
      brief = await fetchBrief();
      await loadHistory();
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
      await loadHistory();
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

  function ontoggle(key: string) {
    expandedKey = expandedKey === key ? null : key;
    focusKey = key;
    if (expandedKey) {
      seen = markSeen(seen, key);
    }
  }

  function onmark(key: string) {
    seen = markSeen(seen, key);
  }

  async function openDrawer(row: BriefTicker) {
    drawerRow = row;
    research = null;
    researchError = null;
    researchLoading = true;
    try {
      const res = await fetchResearch(row.ticker);
      research = res.result;
    } catch (err) {
      researchError = err instanceof Error ? err.message : String(err);
    } finally {
      researchLoading = false;
    }
  }

  function openDrawerByTicker(ticker: string) {
    const row = brief?.tickers.find((t) => t.ticker === ticker);
    if (row) void openDrawer(row);
  }

  function selectHistory(b: DailyBrief) {
    brief = b;
    expandedKey = null;
    focusKey = null;
    drawerRow = null;
  }

  function onKeyNav(e: KeyboardEvent) {
    if (!focusKeys.length) return;
    const tag = (e.target as HTMLElement | null)?.tagName;
    if (tag === "INPUT" || tag === "TEXTAREA") return;
    if (e.key === "j" || e.key === "k") {
      e.preventDefault();
      const idx = focusKey ? focusKeys.indexOf(focusKey) : -1;
      const next =
        e.key === "j"
          ? Math.min(focusKeys.length - 1, Math.max(0, idx + 1))
          : Math.max(0, idx <= 0 ? 0 : idx - 1);
      focusKey = focusKeys[next] ?? null;
    } else if (e.key === "Enter" && focusKey) {
      e.preventDefault();
      ontoggle(focusKey);
    }
  }

  onMount(() => {
    seen = loadSeenKeys();
    void load();
    window.addEventListener("keydown", onKeyNav);
    return () => window.removeEventListener("keydown", onKeyNav);
  });

  const defaultDisclaimer =
    "FolioTracker output is for informational and educational purposes only. It is not investment, legal, or tax advice. Do your own research.";

  const summary = $derived(
    brief?.summary ?? {
      holdings_count: brief?.universe_count ?? 0,
      high_count: 0,
      medium_count: 0,
      quiet_count: brief?.quiet_tickers?.length ?? 0,
      positive_count: 0,
      negative_count: 0,
      neutral_count: 0,
      themes: [] as string[],
      market_risk: "low" as const,
      biggest_story: null,
      biggest_risk: null,
      biggest_opportunity: null,
    },
  );
</script>

<main class="page">
  <header class="hero">
    <p class="brand">FolioTracker</p>
    <PrimaryNav {view} {onnavigate} />
    <p class="tag">
      What changed that matters? Daily Decision Brief — triage, not a news feed.
      Not advice.
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
    <div class="layout">
      <aside class="side">
        <TimelineRail
          {history}
          activeGeneratedAt={brief.generated_at}
          onselect={selectHistory}
        />
      </aside>

      <div class="main-col">
        <PortfolioSummary
          summary={summary}
          generatedAt={brief.generated_at}
          insightMode={brief.insight_mode ?? "deterministic"}
          generationStatus={brief.generation_status}
        />

        {#if brief.morning}
          <MorningCounts morning={brief.morning} />
        {/if}

        <FilterBar active={filter} onchange={(f) => (filter = f)} />

        <HeatMap
          material={brief.tickers}
          quiet={brief.quiet_tickers ?? []}
          onselect={openDrawerByTicker}
        />

        {#if brief.tickers.length === 0 && (brief.quiet_tickers?.length ?? 0) > 0}
          <p class="empty calm">{brief.empty_message ?? "Nothing material in the last 24h."}</p>
        {/if}

        <PrioritySection
          title="High priority"
          headingId="high-priority"
          items={highItems}
          {expandedKey}
          {focusKey}
          {seen}
          {ontoggle}
          onopen={openDrawer}
          {onmark}
        />

        <PrioritySection
          title="Medium priority"
          headingId="medium-priority"
          items={mediumItems}
          {expandedKey}
          {focusKey}
          {seen}
          {ontoggle}
          onopen={openDrawer}
          {onmark}
        />

        <PrioritySection
          title="No important events"
          headingId="quiet"
          quiet={brief.quiet_tickers ?? []}
          {expandedKey}
          {focusKey}
          {seen}
          {ontoggle}
          onopen={openDrawer}
          {onmark}
        />

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
            ranking.
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
      </div>
    </div>
  {/if}

  <DisclaimerBar text={brief?.disclaimer ?? defaultDisclaimer} />
</main>

{#if drawerRow}
  <StockDrawer
    row={drawerRow}
    {research}
    {researchLoading}
    {researchError}
    onclose={() => (drawerRow = null)}
  />
{/if}

<style>
  .page {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    padding: 1.5rem 1.25rem 0;
    max-width: 78rem;
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
  .layout {
    display: grid;
    grid-template-columns: minmax(11rem, 14rem) 1fr;
    gap: 1.5rem;
    align-items: start;
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
  .miss h2 {
    margin: 0 0 0.35rem;
    font-family: var(--font-display);
    font-size: 1.1rem;
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
  @media (max-width: 860px) {
    .layout {
      grid-template-columns: 1fr;
    }
    .side {
      order: -1;
    }
  }
</style>
