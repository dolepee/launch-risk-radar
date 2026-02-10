from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from web3 import Web3


@dataclass(frozen=True)
class Deployment:
    block_number: int
    tx_hash: str
    contract_address: str
    deployer: str


class BaseRPC:
    def __init__(self, rpc_url: str):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))

    def latest_block_number(self) -> int:
        return int(self.w3.eth.block_number)

    def iter_deployments_in_block(self, block_number: int) -> Iterable[Deployment]:
        # Pull full transactions so we can detect contract creations (to == None)
        block = self.w3.eth.get_block(block_number, full_transactions=True)
        for tx in block.transactions:
            # Contract creation tx has `to` == None
            if tx.get("to") is not None:
                continue

            receipt = self.w3.eth.get_transaction_receipt(tx["hash"])
            contract = receipt.get("contractAddress")
            if not contract:
                continue

            yield Deployment(
                block_number=block_number,
                tx_hash=tx["hash"].hex(),
                contract_address=Web3.to_checksum_address(contract),
                deployer=Web3.to_checksum_address(tx["from"]),
            )
