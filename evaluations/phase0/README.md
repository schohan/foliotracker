# Phase 0 evaluations

Eval-first gate for FolioTracker Phase 0. **Review these cases + rubric before implementing** Yahoo tool, cache, or `thesis_agent`.

## Layout

```
evaluations/phase0/
  cases/           # Fixture inputs + expect blocks
  rubrics/         # Human / LLM-judge checklists
  README.md        # This file
```

## Cases

| Case | Intent |
|------|--------|
| `happy_nvda.json` | Full metrics → cited thesis only |
| `partial_metrics.json` | Null fields → no claims on missing data |
| `empty_bundle.json` | Hostile empty evidence → fail closed |
| `multi_evidence_nvda.json` | Financial + news bundle → multi-source citations |
| `conflict_nvda.json` | Conflicting headlines vs financials; conflict item_ids must resolve |

## How to run

```bash
# NOT in default CI (CEO decision 7A)
python -m evaluations.phase0.run
python -m evaluations.phase0.run --case happy_nvda
python -m evaluations.phase0.run --case multi_evidence_nvda
python -m evaluations.phase0.run --case conflict_nvda
```

## CI policy (7A)

| Suite | When |
|-------|------|
| `pytest tests/unit` | Always / CI |
| LLM evals here | On-demand only |

## Pass bar

Cases meet groundedness rubric ≥ 4; conflict fixtures also require every conflict `item_ids` ⊆ bundle evidence ids.
