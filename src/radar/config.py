from __future__ import annotations

from dataclasses import dataclass

from dotenv import load_dotenv
import os


@dataclass(frozen=True)
class Config:
    base_rpc_url: str
    poll_interval_seconds: int
    start_block: str
    alert_min_score: int

    telegram_bot_token: str | None
    telegram_chat_id: str | None

    whatsapp_target: str | None


def load_config() -> Config:
    load_dotenv(override=False)

    return Config(
        base_rpc_url=os.environ.get("BASE_RPC_URL", "https://mainnet.base.org"),
        poll_interval_seconds=int(os.environ.get("POLL_INTERVAL_SECONDS", "30")),
        start_block=os.environ.get("START_BLOCK", "latest"),
        alert_min_score=int(os.environ.get("ALERT_MIN_SCORE", "6")),
        telegram_bot_token=os.environ.get("TELEGRAM_BOT_TOKEN"),
        telegram_chat_id=os.environ.get("TELEGRAM_CHAT_ID"),
        whatsapp_target=os.environ.get("WHATSAPP_TARGET"),
    )
