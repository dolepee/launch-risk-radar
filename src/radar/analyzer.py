"""Two-tier Claude triage: fast scan on every contract, deep analysis when score >= threshold."""
from __future__ import annotations

import json
import httpx
from dataclasses import dataclass

from .basescan import ContractSource


@dataclass(frozen=True)
class RiskAssessment:
    score: int  # 0..10
    headline: str
    tags: list[str]
    details: str
    tier: str  # "fast" or "deep"


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

FAST_SYSTEM = """You are a smart contract security scanner. You receive information about a newly deployed contract on Base (L2). Produce a quick risk triage.

Reply ONLY with valid JSON (no markdown fences):
{
  "score": <0-10 integer>,
  "headline": "<one-line risk summary>",
  "tags": ["<tag1>", "<tag2>", ...]
}

Tags to consider: honeypot, mint-risk, proxy-upgradeable, ownership-not-renounced, fee-manipulation, hidden-mint, reentrancy, flash-loan-risk, fake-liquidity, self-destruct, blacklist-function, pause-function, unverified, safe

Score guide:
- 0-2: appears safe / standard patterns
- 3-5: moderate concerns or unverified
- 6-7: notable risks found
- 8-10: high risk / likely malicious"""

DEEP_SYSTEM = """You are an expert smart contract auditor. Perform a thorough security analysis of this Base contract.

Structure your response as valid JSON (no markdown fences):
{
  "score": <0-10 integer>,
  "headline": "<one-line summary>",
  "tags": ["<tag1>", ...],
  "findings": [
    {
      "severity": "critical|high|medium|low|info",
      "title": "<finding title>",
      "description": "<what the risk is>",
      "evidence": "<function name, line, or pattern>",
      "confidence": "high|medium|low"
    }
  ],
  "summary": "<2-3 paragraph detailed analysis>"
}

Check for: ownership/admin risks, minting capabilities, proxy upgradeability, honeypot patterns (transfer restrictions, hidden fees), reentrancy, flash loan vectors, self-destruct, blacklist/pause functions, fake liquidity locks, and any unusual or obfuscated logic."""


def _build_context(address: str, deployer: str, source: ContractSource | None, bytecode: str | None) -> str:
    """Build the user message with all available contract info."""
    parts = [
        f"Contract address: {address}",
        f"Deployer: {deployer}",
        f"Chain: Base (L2)",
    ]
    if source and source.verified:
        parts.append(f"Contract name: {source.contract_name}")
        parts.append(f"Compiler: {source.compiler_version}")
        parts.append(f"\n--- Verified Source Code ---\n{source.source_code}")
    elif bytecode:
        parts.append(f"\n--- Bytecode (no verified source) ---\n{bytecode[:8000]}")
    else:
        parts.append("\nNo verified source code or bytecode available. Score based on metadata only.")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Claude API call
# ---------------------------------------------------------------------------

ANTHROPIC_API = "https://api.anthropic.com/v1/messages"


async def _call_claude(
    system: str,
    user_msg: str,
    api_key: str,
    max_tokens: int = 1024,
    model: str = "claude-opus-4-6",
) -> dict:
    """Call Anthropic Messages API and parse JSON response."""
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    body = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user_msg}],
    }

    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(ANTHROPIC_API, headers=headers, json=body)
        r.raise_for_status()
        data = r.json()

    text = data["content"][0]["text"].strip()
    # Strip markdown fences if model includes them anyway
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text[:-3]

    return json.loads(text)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def fast_triage(
    address: str,
    deployer: str,
    source: ContractSource | None,
    bytecode: str | None,
    api_key: str,
) -> RiskAssessment:
    """Tier 1: quick risk score (~2-5s, cheap)."""
    ctx = _build_context(address, deployer, source, bytecode)
    try:
        result = await _call_claude(FAST_SYSTEM, ctx, api_key, max_tokens=256, model="claude-sonnet-4-20250514")
        return RiskAssessment(
            score=int(result["score"]),
            headline=result["headline"],
            tags=result.get("tags", []),
            details="",
            tier="fast",
        )
    except Exception as e:
        # Fallback: return neutral score so pipeline doesn't crash
        return RiskAssessment(
            score=5,
            headline=f"Fast triage failed: {e}",
            tags=["triage-error"],
            details=str(e),
            tier="fast",
        )


async def deep_analysis(
    address: str,
    deployer: str,
    source: ContractSource | None,
    bytecode: str | None,
    api_key: str,
) -> RiskAssessment:
    """Tier 2: thorough audit (~10-20s, more expensive). Only called when fast score >= threshold."""
    ctx = _build_context(address, deployer, source, bytecode)
    try:
        result = await _call_claude(DEEP_SYSTEM, ctx, api_key, max_tokens=2048, model="claude-opus-4-6")

        # Build detailed report from findings
        findings_text = ""
        for f in result.get("findings", []):
            findings_text += (
                f"\n[{f['severity'].upper()}] {f['title']}\n"
                f"  {f['description']}\n"
                f"  Evidence: {f.get('evidence', 'N/A')}\n"
                f"  Confidence: {f.get('confidence', 'N/A')}\n"
            )

        details = result.get("summary", "") + "\n\n--- Findings ---" + findings_text

        return RiskAssessment(
            score=int(result["score"]),
            headline=result["headline"],
            tags=result.get("tags", []),
            details=details,
            tier="deep",
        )
    except Exception as e:
        return RiskAssessment(
            score=5,
            headline=f"Deep analysis failed: {e}",
            tags=["analysis-error"],
            details=str(e),
            tier="deep",
        )


# Keep the old placeholder for testing without API key
def quick_heuristic_assess(contract_address: str) -> RiskAssessment:
    return RiskAssessment(
        score=5,
        headline="New contract detected (triage pending)",
        tags=["unverified"],
        details=f"Contract: {contract_address}",
        tier="placeholder",
    )
