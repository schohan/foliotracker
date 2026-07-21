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

## How to run (after thesis_agent exists)

```bash
# NOT in default CI (CEO decision 7A)
python -m evaluations.phase0.run   # to be added at impl time
```

Until the runner exists, review cases manually against the rubric in `rubrics/groundedness.md`.

```bash
python -m evaluations.phase0.run
python -m evaluations.phase0.run --case happy_nvda
```

## CI policy (7A)

| Suite | When |
|-------|------|
| `pytest tests/unit` | Always / CI |
| LLM evals here | On-demand only |

Acceptance specs under `tests/unit/test_yahoo_*.py`, `test_evidence_*.py`, `test_phase0_cache.py`, `test_session_clear.py` are **skipped** until implementation (`Phase 0 implementation pending`). They are the contract for implementers — remove the skip marker as each module lands.

## Pass bar

All three cases meet groundedness rubric ≥ 4 before Phase 0 thesis is considered shippable.
