<script lang="ts">
  import { formatCheckResult, formatFrameworkScore } from "../../thesisFormat";
  import { DRAWER_HELP, helpForCheck } from "../../thesisHelp";
  import type { FrameworkScorecard } from "../../types";
  import HelpTip from "./HelpTip.svelte";

  interface Props {
    scorecard: FrameworkScorecard;
  }

  let { scorecard }: Props = $props();
</script>

<article class="card" aria-label={`${scorecard.label} scorecard`}>
  <header>
    <h3>
      {scorecard.label}
      <HelpTip entry={DRAWER_HELP.framework_score} />
    </h3>
    <p class="headline-score" class:na={scorecard.score == null}>
      {formatFrameworkScore(scorecard.score)}
    </p>
  </header>

  <table>
    <thead>
      <tr>
        <th scope="col">Check</th>
        <th scope="col">Result</th>
      </tr>
    </thead>
    <tbody>
      {#each scorecard.checks as check (check.name)}
        <tr>
          <td>
            <span class="check-name">
              {check.name}
              <HelpTip entry={helpForCheck(check.name)} />
            </span>
            {#if check.detail}
              <span class="detail">{check.detail}</span>
            {/if}
          </td>
          <td class="result" class:pass={check.status === "pass"} class:fail={check.status === "fail"} class:na={check.status === "unknown"}>
            {formatCheckResult(check)}
          </td>
        </tr>
      {/each}
    </tbody>
  </table>

  {#if scorecard.score == null}
    <p class="coverage-note">
      Insufficient data — only {scorecard.coverage}/100 check weight computable
      (score needs ≥ 50).
    </p>
  {/if}
</article>

<style>
  .card {
    border: 1px solid var(--line);
    border-radius: 3px;
    padding: 1rem 1.1rem;
  }
  header {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 0.75rem;
    margin-bottom: 0.6rem;
  }
  h3 {
    margin: 0;
    font-family: var(--font-display);
    font-size: 1.1rem;
    font-weight: 600;
    display: inline-flex;
    align-items: center;
    gap: 0.15rem;
  }
  .headline-score {
    margin: 0;
    font-family: var(--font-display);
    font-size: 1.6rem;
    font-weight: 700;
    color: var(--accent);
  }
  .headline-score.na {
    color: var(--ink-soft);
    font-weight: 400;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.9rem;
  }
  th,
  td {
    text-align: left;
    padding: 0.45rem 0.3rem;
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
  .check-name {
    display: inline-flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.1rem;
    font-weight: 500;
  }
  .detail {
    display: block;
    color: var(--ink-soft);
    font-size: 0.8rem;
    margin-top: 0.15rem;
  }
  .result {
    white-space: nowrap;
    font-weight: 600;
  }
  .result.pass {
    color: var(--ok);
  }
  .result.fail {
    color: var(--error);
  }
  .result.na {
    color: var(--ink-soft);
    font-weight: 400;
  }
  .coverage-note {
    margin: 0.6rem 0 0;
    color: var(--ink-soft);
    font-size: 0.85rem;
    line-height: 1.4;
  }
</style>
