from __future__ import annotations

import httpx

from .analyzer import RiskAssessment
from .base_rpc import Deployment


def format_alert(dep: Deployment, risk: RiskAssessment) -> str:
    return (
        f"🚨 Base contract deployed\n"
        f"Address: {dep.contract_address}\n"
        f"Deployer: {dep.deployer}\n"
        f"Block: {dep.block_number}\n"
        f"Tx: {dep.tx_hash}\n\n"
        f"Risk: {risk.score}/10 — {risk.headline}\n"
        f"Tags: {', '.join(risk.tags)}\n\n"
        f"BaseScan: https://basescan.org/address/{dep.contract_address}\n"
    )


async def send_telegram(bot_token: str, chat_id: str, text: str) -> None:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(url, json={"chat_id": chat_id, "text": text})
        r.raise_for_status()
