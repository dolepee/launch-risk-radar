from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Seen:
    last_block: int


class Store:
    def __init__(self, path: str | Path = "radar.sqlite"):
        self.path = str(path)
        self._init()

    def _init(self) -> None:
        with sqlite3.connect(self.path) as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS meta (
                  k TEXT PRIMARY KEY,
                  v TEXT NOT NULL
                )
                """
            )
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS deployments (
                  tx_hash TEXT PRIMARY KEY,
                  block_number INTEGER NOT NULL,
                  contract_address TEXT NOT NULL,
                  deployer TEXT NOT NULL,
                  created_at INTEGER NOT NULL
                )
                """
            )

    def get_last_block(self) -> int | None:
        with sqlite3.connect(self.path) as con:
            row = con.execute("SELECT v FROM meta WHERE k='last_block'").fetchone()
            return int(row[0]) if row else None

    def set_last_block(self, block: int) -> None:
        with sqlite3.connect(self.path) as con:
            con.execute(
                "INSERT INTO meta(k,v) VALUES('last_block', ?) ON CONFLICT(k) DO UPDATE SET v=excluded.v",
                (str(block),),
            )

    def add_deployment(
        self,
        tx_hash: str,
        block_number: int,
        contract_address: str,
        deployer: str,
        created_at: int,
    ) -> None:
        with sqlite3.connect(self.path) as con:
            con.execute(
                """
                INSERT OR IGNORE INTO deployments(tx_hash, block_number, contract_address, deployer, created_at)
                VALUES(?,?,?,?,?)
                """,
                (tx_hash, block_number, contract_address, deployer, created_at),
            )

    def has_tx(self, tx_hash: str) -> bool:
        with sqlite3.connect(self.path) as con:
            row = con.execute(
                "SELECT 1 FROM deployments WHERE tx_hash=? LIMIT 1",
                (tx_hash,),
            ).fetchone()
            return row is not None
