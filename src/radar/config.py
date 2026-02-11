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
    deep_analysis_threshold: int

    # API keys
    anthropic_api_key: str | None
    basescan_api_key: str | None

    # Channels
    telegram_bot_token: str | None
    telegram_chat_id: str | None
    whatsapp_target: str | None


def load_config() -> Config:
    load_dotenv(override=False)

    return Config(
        base_rpc_url=os.environ.get("BASE_RPC_URL", "https://mainnet.base.org"),
        poll_interval_seconds=int(os.environ.get("POLL_INTERVAL_SECONDS", "30")),
        start_block=os.environ.get("START_BLOCK", "latest"),
        alert_min_score=int(os.environ.get("ALERT_MIN_SCORE", "3")),
        deep_analysis_threshold=int(os.environ.get("DEEP_ANALYSIS_THRESHOLD", "6")),
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
        basescan_api_key=os.environ.get("BASESCAN_API_KEY"),
        telegram_bot_token=os.environ.get("TELEGRAM_BOT_TOKEN"),
        telegram_chat_id=os.environ.get("TELEGRAM_CHAT_ID"),
        whatsapp_target=os.environ.get("WHATSAPP_TARGET"),
    )
