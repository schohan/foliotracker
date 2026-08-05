<script lang="ts">
  import type { BriefBullet, BriefTicker } from "../../types";
  import SourceList from "./SourceList.svelte";

  interface Props {
    row: BriefTicker;
    bullet: BriefBullet;
    expanded: boolean;
    focused: boolean;
    unread: boolean;
    ontoggle: () => void;
    onopen: () => void;
    onmark: () => void;
  }

  let {
    row,
    bullet,
    expanded,
    focused,
    unread,
    ontoggle,
    onopen,
    onmark,
  }: Props = $props();

  function formatPct(v: number | null | undefined): string {
    if (v == null || Number.isNaN(v)) return "—";
    const pct = v * 100;
    const sign = pct > 0 ? "+" : "";
    return `${sign}${pct.toFixed(1)}%`;
  }
</script>

<article
  class="row"
  class:expanded
  class:focused
  class:unread
  class:high={bullet.priority === "high"}
  data-event-key={bullet.event_key}
>
  <button type="button" class="main" onclick={ontoggle} aria-expanded={expanded}>
    <div class="left">
      <span class="ticker">{row.ticker}</span>
      <span class="badge priority">{bullet.priority}</span>
      <span class="badge sentiment {bullet.sentiment}">{bullet.sentiment}</span>
      <span class="list">{row.list_kind}</span>
    </div>
    <div class="mid">
      <span class="headline">{bullet.headline || bullet.category}</span>
      <span class="one">{bullet.one_line_summary || bullet.text}</span>
    </div>
    <div class="right">
      <span class="impact" title="Impact score">{bullet.impact_score}</span>
      <span class="ret">{formatPct(row.daily_return)}</span>
    </div>
  </button>

  {#if expanded}
    <div class="detail">
      <div class="cols">
        <div>
          <h4>Why it matters</h4>
          <ul>
            {#each bullet.why_it_matters as line (line)}
              <li>{line}</li>
            {/each}
          </ul>
          <p class="pi">{bullet.portfolio_impact}</p>
        </div>
        <div>
          <h4>Suggested action</h4>
          <p>{bullet.suggested_action}</p>
          <h4>Confidence</h4>
          <p>{bullet.confidence} · {bullet.insight?.confidence_label ?? "—"}</p>
        </div>
      </div>

      {#if bullet.insight}
        <div class="insight">
          <h4>AI opinion · {bullet.insight.provider}</h4>
          <dl>
            <div><dt>What happened</dt><dd>{bullet.insight.what_happened}</dd></div>
            <div><dt>Why</dt><dd>{bullet.insight.why}</dd></div>
            <div><dt>Market reaction</dt><dd>{bullet.insight.market_reaction}</dd></div>
            <div>
              <dt>Long-term care?</dt>
              <dd>{bullet.insight.should_long_term_care}</dd>
            </div>
            <div><dt>Explain like I'm busy</dt><dd>{bullet.insight.explain_busy}</dd></div>
          </dl>
        </div>
      {/if}

      <div class="actions">
        <h4>Sources</h4>
        <SourceList sources={bullet.sources} />
        <div class="btns">
          <button type="button" class="ghost" onclick={onopen}>Open drawer</button>
          {#if unread}
            <button type="button" class="ghost" onclick={onmark}>Mark read</button>
          {/if}
        </div>
      </div>
    </div>
  {/if}
</article>

<style>
  .row {
    border-bottom: 1px solid var(--line);
  }
  .row.focused {
    background: var(--accent-soft);
  }
  .row.unread .ticker::after {
    content: "";
    display: inline-block;
    width: 6px;
    height: 6px;
    margin-left: 0.35rem;
    border-radius: 50%;
    background: var(--accent);
    vertical-align: middle;
  }
  .main {
    display: grid;
    grid-template-columns: minmax(9rem, 12rem) 1fr auto;
    gap: 0.75rem;
    width: 100%;
    text-align: left;
    border: none;
    background: transparent;
    padding: 0.75rem 0.25rem;
    min-height: 52px;
    color: inherit;
  }
  .left {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 0.35rem 0.45rem;
  }
  .ticker {
    font-family: var(--font-display);
    font-size: 1.15rem;
    font-weight: 600;
  }
  .badge {
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    padding: 0.1rem 0.35rem;
    border: 1px solid var(--line);
    border-radius: 2px;
    color: var(--ink-soft);
  }
  .badge.priority.high {
    border-color: var(--error);
    color: var(--error);
  }
  .badge.sentiment.positive {
    color: var(--ok);
  }
  .badge.sentiment.negative {
    color: var(--error);
  }
  .list {
    font-size: 0.75rem;
    color: var(--ink-soft);
    text-transform: capitalize;
  }
  .mid {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
    min-width: 0;
  }
  .headline {
    font-weight: 550;
    font-size: 0.92rem;
  }
  .one {
    color: var(--ink-soft);
    font-size: 0.85rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .right {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 0.15rem;
    font-variant-numeric: tabular-nums;
  }
  .impact {
    font-family: var(--font-display);
    font-weight: 600;
    font-size: 1.05rem;
  }
  .row.high .impact {
    color: var(--error);
  }
  .ret {
    font-size: 0.82rem;
    color: var(--ink-soft);
  }
  .detail {
    padding: 0 0.25rem 1rem 0.25rem;
    animation: open 0.2s ease;
  }
  @keyframes open {
    from {
      opacity: 0;
      transform: translateY(-4px);
    }
    to {
      opacity: 1;
      transform: none;
    }
  }
  .cols {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
  }
  h4 {
    margin: 0.65rem 0 0.35rem;
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--ink-soft);
    font-weight: 600;
  }
  ul {
    margin: 0;
    padding-left: 1.1rem;
    font-size: 0.9rem;
  }
  .pi,
  .detail p {
    margin: 0.25rem 0 0;
    font-size: 0.9rem;
  }
  .insight {
    margin-top: 0.75rem;
    padding-top: 0.5rem;
    border-top: 1px solid var(--line);
  }
  .insight dl {
    margin: 0;
    display: grid;
    gap: 0.35rem;
  }
  .insight div {
    display: grid;
    grid-template-columns: 8.5rem 1fr;
    gap: 0.5rem;
    font-size: 0.88rem;
  }
  .insight dt {
    color: var(--ink-soft);
  }
  .insight dd {
    margin: 0;
  }
  .btns {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin-top: 0.65rem;
  }
  .ghost {
    border: 1px solid var(--line);
    background: white;
    color: var(--ink);
    border-radius: 2px;
    padding: 0.4rem 0.7rem;
    min-height: 40px;
    font-size: 0.85rem;
  }
  @media (max-width: 720px) {
    .main {
      grid-template-columns: 1fr;
    }
    .right {
      flex-direction: row;
      justify-content: space-between;
      width: 100%;
    }
    .cols,
    .insight div {
      grid-template-columns: 1fr;
    }
    .one {
      white-space: normal;
    }
  }
</style>
