"""Small persistent account store for the standalone application."""

import sqlite3
import os
from pathlib import Path


class AccountStore:
    def __init__(self, path: str | None = None):
        target = Path(path or os.getenv("LOANSERVE_ACCOUNT_DATABASE", "database/accounts.db"))
        target.parent.mkdir(parents=True, exist_ok=True)
        self.path = target
        with self._connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS accounts ("
                "user_name TEXT PRIMARY KEY, password_hash TEXT NOT NULL, role TEXT NOT NULL)"
            )

    def _connect(self):
        return sqlite3.connect(self.path, timeout=10)

    def get(self, user_name):
        with self._connect() as connection:
            row = connection.execute(
                "SELECT password_hash, role FROM accounts WHERE user_name = ?", (user_name,)
            ).fetchone()
        return {"password_hash": row[0], "role": row[1]} if row else None

    def count(self):
        with self._connect() as connection:
            return connection.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]

    def create(self, user_name, password_hash, role):
        try:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO accounts (user_name, password_hash, role) VALUES (?, ?, ?)",
                    (user_name, password_hash, role),
                )
        except sqlite3.IntegrityError:
            return False
        return True
