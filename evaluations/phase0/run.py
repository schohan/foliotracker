"""Phase 0 LLM eval runner (on-demand — not default CI).

Usage:
  python -m evaluations.phase0.run
  python -m evaluations.phase0.run --case happy_nvda

Requires GOOGLE_API_KEY. Loads fixture EvidenceBundle and calls generate_thesis.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.agents.report.thesis_agent import generate_thesis
from app.schemas.evidence import EvidenceBundle
from app.schemas.phase0 import PHASE0_DISCLAIMER, Phase0Result, Phase0Status

CASES_DIR = Path(__file__).parent / "cases"


def _load_case(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _score_case(case: dict, result: Phase0Result) -> tuple[bool, list[str]]:
    expect = case["expect"]
    problems: list[str] = []

    if result.status.value not in expect.get("status_in", []):
        problems.append(
            f"status {result.status.value} not in {expect.get('status_in')}"
        )
    if expect.get("disclaimer_present") and result.disclaimer != PHASE0_DISCLAIMER:
        problems.append("disclaimer missing or wrong")
    if expect.get("request_id_present") and not result.request_id:
        problems.append("request_id missing")
    if "cache_hit" in expect and result.cache_hit != expect["cache_hit"]:
        problems.append(f"cache_hit expected {expect['cache_hit']}")

    if expect.get("all_claim_evidence_ids_in_bundle") and result.thesis and result.evidence:
        known = {i.id for i in result.evidence.items}
        for claim in result.thesis.claims:
            missing = set(claim.evidence_ids) - known
            if missing:
                problems.append(f"dangling ids: {missing}")

    if expect.get("thesis_null_or_no_material_claims"):
        if result.thesis and result.thesis.claims:
            problems.append("expected no material thesis claims for empty bundle")

    return (len(problems) == 0, problems)


def run_case(path: Path) -> bool:
    case = _load_case(path)
    print(f"== {case['id']}: {case['description']}")
    bundle = EvidenceBundle.model_validate(case["input"]["evidence_bundle"])

    if not bundle.items:
        result = Phase0Result(
            ticker=bundle.ticker,
            status=Phase0Status.ERROR,
            evidence=bundle,
            thesis=None,
            error_message="empty evidence bundle",
            request_id="eval-empty",
            cache_hit=False,
        )
    else:
        thesis = generate_thesis(bundle)
        status = (
            Phase0Status.PARTIAL
            if bundle.status.value == "partial"
            else Phase0Status.OK
        )
        result = Phase0Result(
            ticker=bundle.ticker,
            status=status,
            evidence=bundle,
            thesis=thesis,
            request_id=f"eval-{case['id']}",
            cache_hit=False,
        )

    ok, problems = _score_case(case, result)
    if ok:
        print("PASS")
    else:
        print("FAIL")
        for p in problems:
            print(f"  - {p}")
        if result.thesis:
            print(result.thesis.model_dump_json(indent=2))
    return ok


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Phase 0 LLM evals")
    parser.add_argument("--case", help="Case id (filename stem), default=all")
    args = parser.parse_args(argv)

    paths = sorted(CASES_DIR.glob("*.json"))
    if args.case:
        paths = [CASES_DIR / f"{args.case}.json"]
        if not paths[0].exists():
            print(f"unknown case: {args.case}", file=sys.stderr)
            return 2

    results = [run_case(p) for p in paths]
    passed = sum(1 for r in results if r)
    print(f"\n{passed}/{len(results)} passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
