from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RiskAssessment:
    score: int  # 0..10
    headline: str
    tags: list[str]
    details: str


def quick_heuristic_assess(contract_address: str) -> RiskAssessment:
    # MVP placeholder: we will replace/augment this with Claude triage + BaseScan enrichment.
    # For now, emit a neutral score so the pipeline is end-to-end.
    return RiskAssessment(
        score=5,
        headline="New contract detected (triage pending)",
        tags=["unverified"],
        details=f"Contract: {contract_address}\n\nNext: pull verified source (BaseScan) + run Claude triage.",
    )
