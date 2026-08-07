<script lang="ts">
  import { formatMoney, formatMosStars } from "../../thesisFormat";
  import type { MarginOfSafetyView } from "../../types";

  interface Props {
    view: MarginOfSafetyView;
  }

  let { view }: Props = $props();
</script>

<article class="panel" aria-label="Margin of Safety">
  <header>
    <h3>Margin of Safety</h3>
    {#if view.rating}
      <p class="rating">{view.rating}</p>
    {/if}
  </header>

  <dl class="rows">
    <div>
      <dt>Intrinsic Value</dt>
      <dd class:na={view.intrinsic_value == null}>
        {formatMoney(view.intrinsic_value)}
      </dd>
    </div>
    <div>
      <dt>Market Price</dt>
      <dd class:na={view.market_price == null}>{formatMoney(view.market_price)}</dd>
    </div>
    <div>
      <dt>Margin of Safety</dt>
      <dd class:na={view.margin_of_safety == null}>
        {#if view.margin_of_safety == null}
          —
        {:else}
          {(view.margin_of_safety * 100).toFixed(0)}%
        {/if}
      </dd>
    </div>
    <div>
      <dt>Stars</dt>
      <dd class="stars" class:na={view.stars == null} aria-label={view.stars != null ? `${view.stars} of 5 stars` : "unavailable"}>
        {formatMosStars(view.stars)}
      </dd>
    </div>
  </dl>

  {#if view.detail}
    <p class="detail">{view.detail}</p>
  {/if}
</article>

<style>
  .panel {
    border: 1px solid var(--line);
    border-radius: 3px;
    padding: 1rem 1.1rem;
  }
  header {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    justify-content: space-between;
    gap: 0.5rem;
    margin-bottom: 0.75rem;
  }
  h3 {
    margin: 0;
    font-family: var(--font-display);
    font-size: 1.1rem;
    font-weight: 600;
  }
  .rating {
    margin: 0;
    font-weight: 600;
    color: var(--accent);
  }
  .rows {
    margin: 0;
    display: grid;
    gap: 0.45rem;
  }
  .rows > div {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    padding: 0.35rem 0;
    border-bottom: 1px solid var(--line);
    font-size: 0.95rem;
  }
  dt {
    color: var(--ink-soft);
    font-weight: 500;
  }
  dd {
    margin: 0;
    font-weight: 600;
    font-family: var(--font-display);
  }
  dd.na {
    color: var(--ink-soft);
    font-weight: 400;
    font-family: var(--font-body);
  }
  .stars {
    letter-spacing: 0.08em;
    color: var(--accent);
  }
  .detail {
    margin: 0.65rem 0 0;
    color: var(--ink-soft);
    font-size: 0.85rem;
    line-height: 1.4;
  }
</style>
