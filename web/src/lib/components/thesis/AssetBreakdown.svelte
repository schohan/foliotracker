<script lang="ts">
  import {
    formatAssetVerdict,
    formatDifferencePct,
    formatMoney,
  } from "../../thesisFormat";
  import type { AssetBreakdown } from "../../types";

  interface Props {
    breakdown: AssetBreakdown;
  }

  let { breakdown }: Props = $props();
</script>

<article class="panel" aria-label="Asset breakdown">
  <header>
    <h3>Net Asset Intelligence</h3>
    {#if breakdown.verdict}
      <p class="verdict">{formatAssetVerdict(breakdown.verdict)}</p>
    {/if}
  </header>

  <div class="cols">
    <section aria-labelledby="assets-heading">
      <h4 id="assets-heading">Assets</h4>
      <table>
        <tbody>
          {#each breakdown.assets as line (line.name)}
            <tr>
              <td>{line.name}</td>
              <td class="value" class:na={line.value == null}>
                {formatMoney(line.value)}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </section>

    <section aria-labelledby="liab-heading">
      <h4 id="liab-heading">Liabilities</h4>
      <table>
        <tbody>
          {#each breakdown.liabilities as line (line.name)}
            <tr>
              <td>{line.name}</td>
              <td class="value" class:na={line.value == null}>
                {formatMoney(line.value)}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </section>
  </div>

  <dl class="summary">
    <div>
      <dt>Market Cap</dt>
      <dd class:na={breakdown.market_cap == null}>
        {formatMoney(breakdown.market_cap)}
      </dd>
    </div>
    <div>
      <dt>Adjusted Net Assets</dt>
      <dd class:na={breakdown.adjusted_net_assets == null}>
        {formatMoney(breakdown.adjusted_net_assets)}
      </dd>
    </div>
    <div>
      <dt>Difference</dt>
      <dd class:na={breakdown.difference_pct == null}>
        {formatDifferencePct(breakdown.difference_pct)}
      </dd>
    </div>
  </dl>

  {#if breakdown.detail}
    <p class="detail">{breakdown.detail}</p>
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
  .verdict {
    margin: 0;
    font-weight: 600;
    color: var(--accent);
  }
  .cols {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr));
    gap: 1rem;
    margin-bottom: 0.75rem;
  }
  h4 {
    margin: 0 0 0.4rem;
    font-size: 0.75rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--ink-soft);
  }
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.9rem;
  }
  td {
    padding: 0.35rem 0.2rem;
    border-bottom: 1px solid var(--line);
  }
  .value {
    text-align: right;
    font-weight: 600;
    white-space: nowrap;
  }
  .value.na {
    color: var(--ink-soft);
    font-weight: 400;
  }
  .summary {
    margin: 0;
    display: grid;
    gap: 0.4rem;
  }
  .summary > div {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    padding: 0.4rem 0;
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
  .detail {
    margin: 0.65rem 0 0;
    color: var(--ink-soft);
    font-size: 0.85rem;
    line-height: 1.4;
  }
</style>
