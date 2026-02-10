from __future__ import annotations

import asyncio
import time

from rich.console import Console

from .analyzer import quick_heuristic_assess
from .base_rpc import BaseRPC
from .config import load_config
from .publishers import format_alert, send_telegram, send_whatsapp
from .store import Store

console = Console()


async def run_loop() -> None:
    cfg = load_config()
    rpc = BaseRPC(cfg.base_rpc_url)
    store = Store()

    if cfg.start_block == "latest":
        last = store.get_last_block() or rpc.latest_block_number()
    else:
        last = int(cfg.start_block)

    console.print(f"[bold]Launch Risk Radar[/bold]")
    console.print(f"RPC: {cfg.base_rpc_url}")
    console.print(f"Starting from block: {last}")
    console.print(f"Poll interval: {cfg.poll_interval_seconds}s")

    while True:
        latest = rpc.latest_block_number()
        if last < latest:
            for bn in range(last + 1, latest + 1):
                for dep in rpc.iter_deployments_in_block(bn):
                    if store.has_tx(dep.tx_hash):
                        continue

                    risk = quick_heuristic_assess(dep.contract_address)
                    msg = format_alert(dep, risk)

                    # persist
                    store.add_deployment(
                        tx_hash=dep.tx_hash,
                        block_number=dep.block_number,
                        contract_address=dep.contract_address,
                        deployer=dep.deployer,
                        created_at=int(time.time()),
                    )

                    # publish
                    console.print(msg)
                    if risk.score >= cfg.alert_min_score:
                        if cfg.telegram_bot_token and cfg.telegram_chat_id:
                            await send_telegram(cfg.telegram_bot_token, cfg.telegram_chat_id, msg)
                        if cfg.whatsapp_target:
                            await send_whatsapp(cfg.whatsapp_target, msg)

                store.set_last_block(bn)
            last = latest

        await asyncio.sleep(cfg.poll_interval_seconds)


def main() -> None:
    asyncio.run(run_loop())
