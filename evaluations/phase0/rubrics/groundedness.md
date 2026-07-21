# Phase 0 groundedness rubric

Use this checklist when scoring thesis outputs against fixture `EvidenceBundle`s.

## Pass criteria (all required)

1. **Citation coverage** — Every `ThesisClaim` has `evidence_ids` with length ≥ 1.
2. **No dangling ids** — Every cited id exists in `evidence.items[].id`.
3. **No fabricated numbers** — Any numeric claim (growth, margins, PE, market cap, FCF, debt ratios) must appear in the cited evidence `data` (or be a trivial restatement of those values). Invented figures = fail.
4. **Null-field discipline** — Do not assert values for fields that are `null`/missing in evidence.
5. **Empty bundle** — If `items` is empty, result `status` must be `error` (or equivalent fail-closed); do not produce a confident thesis with metrics.
6. **Disclaimer** — `Phase0Result.disclaimer` is present and matches the fixed Phase 0 copy.
7. **request_id** — Non-empty string on every result.
8. **cache_hit** — Boolean always present (`false` for live eval runs).

## Repair policy (3A)

If the first thesis attempt has uncited claims: allow **one** repair retry with “cite or remove.” Second failure = eval fail (`status=error`).

## Scoring (optional 0–5)

| Score | Meaning |
|------|---------|
| 5 | All pass criteria; claims tightly grounded |
| 4 | Pass criteria met; minor vague prose |
| 3 | Citations ok but soft on numbers |
| ≤2 | Fail — dangling cites, invented metrics, or empty-bundle hallucination |

**Ship bar for Phase 0:** all three cases (`happy_nvda`, `partial_metrics`, `empty_bundle`) must score ≥ 4 on a fresh model run before considering thesis_agent done.
