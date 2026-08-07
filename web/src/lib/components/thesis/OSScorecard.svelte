<script lang="ts">
  import { formatFrameworkScore } from "../../thesisFormat";
  import type { InvestmentOSScore } from "../../types";

  interface Props {
    score: InvestmentOSScore;
  }

  let { score }: Props = $props();
</script>

<article class="panel" aria-label="Investment OS Score">
  <header>
    <h3>Investment OS Score</h3>
    <div class="headline">
      <span class="score" class:na={score.score == null}>
        {formatFrameworkScore(score.score)}
      </span>
      {#if score.rating}
        <span class="rating">{score.rating}</span>
      {/if}
    </div>
    <p class="meta">Coverage {score.coverage}/100 · weighted composite</p>
  </header>

  <table>
    <thead>
      <tr>
        <th scope="col">Dimension</th>
        <th scope="col">Wt</th>
        <th scope="col">Points</th>
      </tr>
    </thead>
    <tbody>
      {#each score.dimensions as dim (dim.id)}
        <tr>
          <td>
            <span class="name">{dim.label}</span>
            {#if dim.detail}
              <span class="detail">{dim.detail}</span>
            {/if}
          </td>
          <td class="wt">{dim.weight}</td>
          <td class="pts" class:na={dim.points == null}>
            {formatFrameworkScore(dim.points)}
          </td>
        </tr>
      {/each}
    </tbody>
  </table>
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
    margin: 0 0 0.4rem;
    font-family: var(--font-display);
    font-size: 1.1rem;
    font-weight: 600;
  }
  .headline {
    display: flex;
    align-items: baseline;
    gap: 0.55rem;
  }
  .score {
    font-family: var(--font-display);
    font-size: 1.8rem;
    font-weight: 700;
    line-height: 1;
  }
  .score.na {
    color: var(--ink-soft);
    font-weight: 400;
  }
  .rating {
    font-weight: 600;
    color: var(--accent);
  }
  .meta {
    margin: 0.35rem 0 0;
    color: var(--ink-soft);
    font-size: 0.85rem;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.9rem;
  }
  th,
  td {
    text-align: left;
    padding: 0.4rem 0.25rem;
    border-bottom: 1px solid var(--line);
    vertical-align: top;
  }
  th {
    color: var(--ink-soft);
    font-weight: 500;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }
  .name {
    display: block;
    font-weight: 500;
  }
  .detail {
    display: block;
    color: var(--ink-soft);
    font-size: 0.8rem;
    margin-top: 0.15rem;
  }
  .wt,
  .pts {
    white-space: nowrap;
    font-weight: 600;
  }
  .pts.na {
    color: var(--ink-soft);
    font-weight: 400;
  }
</style>
