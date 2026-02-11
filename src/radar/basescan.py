"""BaseScan API client for contract source enrichment."""
from __future__ import annotations

import httpx
from dataclasses import dataclass


@dataclass(frozen=True)
class ContractSource:
    verified: bool
    source_code: str | None  # Solidity source (None if unverified)
    contract_name: str | None
    compiler_version: str | None
    abi: str | None


BASESCAN_API = "https://api.basescan.org/api"


async def fetch_contract_source(
    address: str, api_key: str | None = None
) -> ContractSource:
    """Fetch verified source code from BaseScan. Returns unverified stub if unavailable."""
    params: dict[str, str] = {
        "module": "contract",
        "action": "getsourcecode",
        "address": address,
    }
    if api_key:
        params["apikey"] = api_key

    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(BASESCAN_API, params=params)
        r.raise_for_status()
        data = r.json()

    # BaseScan returns result as a list with one item
    if data.get("status") != "1" or not data.get("result"):
        return ContractSource(verified=False, source_code=None, contract_name=None,
                              compiler_version=None, abi=None)

    item = data["result"][0]
    source = item.get("SourceCode", "")
    if not source or source == "":
        return ContractSource(verified=False, source_code=None, contract_name=None,
                              compiler_version=None, abi=None)

    return ContractSource(
        verified=True,
        source_code=source[:50_000],  # cap to avoid huge payloads
        contract_name=item.get("ContractName"),
        compiler_version=item.get("CompilerVersion"),
        abi=item.get("ABI"),
    )


async def fetch_contract_bytecode(address: str, api_key: str | None = None) -> str | None:
    """Fetch deployed bytecode from BaseScan."""
    params: dict[str, str] = {
        "module": "proxy",
        "action": "eth_getCode",
        "address": address,
        "tag": "latest",
    }
    if api_key:
        params["apikey"] = api_key

    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(BASESCAN_API, params=params)
        r.raise_for_status()
        data = r.json()

    code = data.get("result", "0x")
    if code in ("0x", "0x0", None, ""):
        return None
    return code[:20_000]  # cap for prompt size
