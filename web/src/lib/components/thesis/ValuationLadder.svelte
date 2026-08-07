<script lang="ts">
  import { formatMoney } from "../../thesisFormat";
  import { DRAWER_HELP, helpForLadderRung } from "../../thesisHelp";
  import type { ValuationLadder } from "../../types";
  import HelpTip from "./HelpTip.svelte";

  interface Props {
    ladder: ValuationLadder;
  }

  let { ladder }: Props = $props();

  const rungs: { key: keyof ValuationLadder; label: string }[] = [
    { key: "market", label: "Market Price" },
    { key: "intrinsic", label: "Intrinsic Value" },
    { key: "liquidation", label: "Liquidation Value" },
    { key: "replacement", label: "Replacement Value" },
    { key: "enterprise", label: "Enterprise Value" },
    { key: "expected_fair", label: "Expected Fair Value" },
  ];
</script>

<article class="panel" aria-label="Valuation ladder">
  <header>
    <h3>
      Valuation ladder
      <HelpTip entry={DRAWER_HELP.valuation_ladder} />
    </h3>
  </header>
  <table>
    <thead>
      <tr>
        <th scope="col">Rung</th>
        <th scope="col">Firm value</th>
      </tr>
    </thead>
    <tbody>
      {#each rungs as rung (rung.key)}
        <tr>
          <td>
            <span class="rung">
              {rung.label}
              <HelpTip entry={helpForLadderRung(rung.key)} />
            </span>
          </td>
          <td class="value" class:na={ladder[rung.key] == null}>
            {formatMoney(ladder[rung.key])}
          </td>
        </tr>
      {/each}
    </tbody>
  </table>
  <p class="note">
    Replacement Value is unavailable until a method is locked. “—” means
    insufficient data — never invented.
  </p>
</article>

<style>
  .panel {
    border: 1px solid var(--line);
    border-radius: 3px;
    padding: 1rem 1.1rem;
  }
  header {
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
  }
  th {
    color: var(--ink-soft);
    font-weight: 500;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }
  .rung {
    display: inline-flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.1rem;
  }
  .value {
    font-weight: 600;
    white-space: nowrap;
  }
  .value.na {
    color: var(--ink-soft);
    font-weight: 400;
  }
  .note {
    margin: 0.6rem 0 0;
    color: var(--ink-soft);
    font-size: 0.85rem;
    line-height: 1.4;
  }
</style>
