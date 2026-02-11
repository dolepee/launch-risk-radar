"""Main loop: watch Base blocks → enrich → fast triage → (optional) deep analysis → alert."""
from __future__ import annotations

import asyncio
import time

from rich.console import Console

from .analyzer import fast_triage, deep_analysis, quick_heuristic_assess
from .base_rpc import BaseRPC, Deployment
from .basescan import fetch_contract_source, fetch_contract_bytecode
from .config import Config, load_config
from .publishers import format_fast_alert, format_deep_alert, send_telegram, send_whatsapp
from .store import Store

console = Console()


async def enrich_and_triage(dep: Deployment, cfg: Config) -> None:
    """Full pipeline for one deployment: enrich → fast triage → deep if needed → publish."""

    # Step 1: Enrich from BaseScan
    source = None
    bytecode = None
    try:
        source = await fetch_contract_source(dep.contract_address, cfg.basescan_api_key)
        if not source.verified:
            bytecode = await fetch_contract_bytecode(dep.contract_address, cfg.basescan_api_key)
    except Exception as e:
        console.print(f"[yellow]BaseScan enrichment failed for {dep.contract_address}: {e}[/yellow]")

    # Step 2: Fast triage (always)
    if cfg.anthropic_api_key:
        risk = await fast_triage(
            dep.contract_address, dep.deployer, source, bytecode, cfg.anthropic_api_key
        )
    else:
        risk = quick_heuristic_assess(dep.contract_address)

    console.print(
        f"[{'red' if risk.score >= 7 else 'yellow' if risk.score >= 4 else 'green'}]"
        f"FAST {risk.score}/10 — {risk.headline} [{dep.contract_address[:10]}…][/]"
    )

    # Step 3: Publish fast alert (if above min score)
    if risk.score >= cfg.alert_min_score:
        fast_msg = format_fast_alert(dep, risk)
        await _publish(cfg, fast_msg)

    # Step 4: Deep analysis (if score >= threshold)
    if risk.score >= cfg.deep_analysis_threshold and cfg.anthropic_api_key:
        console.print(f"[bold magenta]Triggering deep analysis for {dep.contract_address[:10]}…[/bold magenta]")
        deep_risk = await deep_analysis(
            dep.contract_address, dep.deployer, source, bytecode, cfg.anthropic_api_key
        )
        console.print(
            f"[bold]DEEP {deep_risk.score}/10 — {deep_risk.headline}[/bold]"
        )
        deep_msg = format_deep_alert(dep, deep_risk)
        await _publish(cfg, deep_msg)


async def _publish(cfg: Config, msg: str) -> None:
    """Send alert to configured channels."""
    tasks = []
    if cfg.telegram_bot_token and cfg.telegram_chat_id:
        tasks.append(send_telegram(cfg.telegram_bot_token, cfg.telegram_chat_id, msg))
    if cfg.whatsapp_target:
        tasks.append(send_whatsapp(cfg.whatsapp_target, msg))
    if tasks:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, Exception):
                console.print(f"[red]Publish error: {r}[/red]")


async def run_loop() -> None:
    cfg = load_config()
    rpc = BaseRPC(cfg.base_rpc_url)
    store = Store()

    if cfg.start_block == "latest":
        last = store.get_last_block() or rpc.latest_block_number()
    else:
        last = int(cfg.start_block)

    console.print(f"[bold]🚀 Launch Risk Radar v0.2[/bold]")
    console.print(f"RPC: {cfg.base_rpc_url}")
    console.print(f"Starting from block: {last}")
    console.print(f"Poll: {cfg.poll_interval_seconds}s | Alert ≥ {cfg.alert_min_score} | Deep ≥ {cfg.deep_analysis_threshold}")
    console.print(f"BaseScan: {'✅' if cfg.basescan_api_key else '❌'} | Claude: {'✅' if cfg.anthropic_api_key else '❌'}")
    console.print(f"Telegram: {'✅' if cfg.telegram_bot_token else '❌'} | WhatsApp: {'✅' if cfg.whatsapp_target else '❌'}")

    while True:
        try:
            latest = rpc.latest_block_number()
            if last < latest:
                # Process max 10 blocks per cycle to avoid long stalls
                end = min(latest, last + 10)
                for bn in range(last + 1, end + 1):
                    for dep in rpc.iter_deployments_in_block(bn):
                        if store.has_tx(dep.tx_hash):
                            continue

                        # Persist first (so we don't re-process on crash)
                        store.add_deployment(
                            tx_hash=dep.tx_hash,
                            block_number=dep.block_number,
                            contract_address=dep.contract_address,
                            deployer=dep.deployer,
                            created_at=int(time.time()),
                        )

                        # Triage + publish
                        await enrich_and_triage(dep, cfg)

                    store.set_last_block(bn)
                last = end
        except Exception as e:
            console.print(f"[red]Loop error: {e}[/red]")

        await asyncio.sleep(cfg.poll_interval_seconds)


def main() -> None:
    asyncio.run(run_loop())
