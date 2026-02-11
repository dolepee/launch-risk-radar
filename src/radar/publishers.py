"""Alert formatting and publishing to Telegram + WhatsApp."""
from __future__ import annotations

import asyncio
import httpx

from .analyzer import RiskAssessment
from .base_rpc import Deployment


def format_fast_alert(dep: Deployment, risk: RiskAssessment) -> str:
    """Short alert for fast triage results."""
    emoji = "🔴" if risk.score >= 7 else "🟡" if risk.score >= 4 else "🟢"
    return (
        f"{emoji} New Base contract\n"
        f"Risk: {risk.score}/10 — {risk.headline}\n"
        f"Tags: {', '.join(risk.tags)}\n\n"
        f"Address: {dep.contract_address}\n"
        f"Deployer: {dep.deployer}\n"
        f"Block: {dep.block_number}\n"
        f"BaseScan: https://basescan.org/address/{dep.contract_address}\n"
    )


def format_deep_alert(dep: Deployment, risk: RiskAssessment) -> str:
    """Rich alert for deep analysis results."""
    emoji = "🔴" if risk.score >= 7 else "🟡" if risk.score >= 4 else "🟢"
    header = (
        f"{emoji} DEEP ANALYSIS — Risk {risk.score}/10\n"
        f"{risk.headline}\n"
        f"Tags: {', '.join(risk.tags)}\n\n"
        f"Contract: {dep.contract_address}\n"
        f"Deployer: {dep.deployer}\n"
        f"BaseScan: https://basescan.org/address/{dep.contract_address}\n"
    )
    if risk.details:
        # Truncate for messaging (WhatsApp/Telegram have limits)
        details = risk.details[:2000]
        header += f"\n--- Report ---\n{details}\n"
    return header


# Legacy format (kept for compatibility)
def format_alert(dep: Deployment, risk: RiskAssessment) -> str:
    if risk.tier == "deep":
        return format_deep_alert(dep, risk)
    return format_fast_alert(dep, risk)


async def send_telegram(bot_token: str, chat_id: str, text: str) -> None:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    # Truncate to Telegram's 4096 char limit
    if len(text) > 4000:
        text = text[:4000] + "\n…(truncated)"
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(url, json={"chat_id": chat_id, "text": text})
        r.raise_for_status()


async def send_whatsapp(target: str, text: str) -> None:
    """Send a WhatsApp DM via the local OpenClaw gateway."""
    proc = await asyncio.create_subprocess_exec(
        "/home/ubuntu/.npm-global/bin/openclaw",
        "message",
        "send",
        "--channel",
        "whatsapp",
        "--target",
        target,
        "--message",
        text,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _out, err = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"openclaw message send failed: {err.decode('utf-8', 'ignore')}")
